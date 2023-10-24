from gedcom.element.element import Element
from gedcom.element.family import FamilyElement
from gedcom.element.file import FileElement
from gedcom.element.object import ObjectElement
from gedcom.element.individual import IndividualElement
from gedcom.parser import Parser
import gedcom.tags
import pickle

import pandas as pd

import glob, os
import re
import datetime
import uuid
import random
import json
from tqdm import tqdm

from dateutil.parser import parse

uuids = {}
min_words = 5
#gedcom_folder = '/home/omri/GNN/GedcomFiles/'
#output_folder = '/home/omri/GNN/Code/Dataset/texts2/'
gedcom_folder = '/home/omri/GNN/GedIndex/'
output_folder = '/home/omri/GNN/Code/Dataset/GedIndexTexts2/'
regex = re.compile('[^a-zA-Z ]')

person_cache = {}

def is_date(string, fuzzy=False):
    """
    Return whether the string can be interpreted as a date.

    :param string: str, string to check for date
    :param fuzzy: bool, ignore unknown tokens in string if True
    """
    try: 
        parse(string, fuzzy=fuzzy)
        return True
    except:
        return False

def text_is_relevant(val, text, func_to_compare):
    t = val
    t2 = text
    if func_to_compare(re.sub(' +', ' ', t).lower().strip(), re.sub(' +', ' ', t2).lower().strip()):
        return True
    t = regex.sub('', val)
    if func_to_compare(re.sub(' +', ' ', t).lower().strip(), re.sub(' +', ' ', t2).lower().strip()):
        return True
    t2 = regex.sub('', text)
    if func_to_compare(re.sub(' +', ' ', t).lower().strip(), re.sub(' +', ' ', t2).lower().strip()):
        return True
    t = val
    t2 = text
    t = regex.sub(' ', val)
    if func_to_compare(re.sub(' +', ' ', t).lower().strip(), re.sub(' +', ' ', t2).lower().strip()):
        return True
    t2 = regex.sub(' ', text)
    if func_to_compare(re.sub(' +', ' ', t).lower().strip(), re.sub(' +', ' ', t2).lower().strip()):
        return True
    return False

def text_are_same(t1,t2):
    return t1 == t2
def text_contains(t1,t2):
    return t1 in t2 or t2 in t1

def clean_string(val, ignore_exact_values):

    if val is not None:
        val = val.replace('\n', ' ').replace('\r', ' ')
    else:
        val = ''
    
    val = val.strip()
    val = re.sub(' +', ' ', val)

    for ignoretext in ignore_exact_values:
        if text_is_relevant(val, ignoretext,text_are_same) == True:
            val = ''
            break

    if val.startswith('http') == True:
        val = ''
   
    val = val.strip()

    if is_date(val):
        val =''
    
    if get_words_count(val) < min_words:
        val = ''

    return val

def get_gedcom_full_value(elm, ignore_exact_values):
    val = clean_string(elm.get_multi_line_value(), ignore_exact_values)   

    for c in elm.get_child_elements():
        val = val + ' ' + get_gedcom_full_value(c,ignore_exact_values)
    return val

def get_words_count(val):
    return min(len(regex.sub(' ', val).split()),len(val.split()))

def check_att_found(val, att):
    return len(att) > 0 and text_is_relevant(val, att,text_contains)

def capital_word(s):
    lst = [word[0].upper() + word[1:].lower() for word in s.split()]
    s = " ".join(lst)
    return s

def get_smal_uuid():
    small_id = str(uuid.uuid4().hex)[:24]
    if small_id not in uuids:
        uuids[small_id] = True
        return small_id
    else:
        while small_id in uuids:
            small_id = str(uuid.uuid4().hex)[:24]
            if small_id not in uuids:
                uuids[small_id] = True
                return small_id

def create_answer(text, index):
    return {
        "text": text,
        "answer_start": index
    }
def create_qa(question, answers):
    return {
        "question":re.sub(' +', ' ', question),
        "id" : get_smal_uuid(),
        "answers": answers,
        "is_impossible":False
    }

def findall(substring, string):
    #try:
    if 1 ==1:
        length = len(substring)
        c=0
        indexes = []
        while c < len(string):
            if string[c:c+length] == substring:
                indexes.append(c)
            c=c+1
        return indexes
    #except:
    #    return []

def create_value_answers(val,c):
    name_answers = []
    if len(c) > 0 and len(val) > 0:
        name_index = findall(val, c)
        if len(name_index) > 0:
            for i in name_index:
                name_answers.append(create_answer(val, i))
    return name_answers

def get_string(v):
    if type(v) == str:
        return v
    else:
        return v.decode('utf-8')

def get_parents(parents, first_name, depth):
        p_names = ''
        sep = ''
        for p in parents:
            p_names = p_names + sep + p.get_name()
            sep = ' and '

        if len(parents) == 1:
            p_names = p_names + ' was ' + first_name + "'s "
            if depth == 1:
                p_names = p_names + parents[0].get_name_as_a_parent()
            else:
                p_names = p_names + parents[0].get_name_as_a_grandparent()

        elif len(parents) > 1:
            p_names = p_names + ' were ' + first_name + "'s "
            if depth == 1:
                p_names = p_names + "parents"
            else:
                p_names = p_names + "grandparents"
        
        return p_names

def get_children(children, first_name, depth):
    ch_names = ''
    sep = ''
    for ch in children:
        ch_names = ch_names + sep + ch.get_name()
        sep = ' and '

    if len(children) == 1:
        ch_names = ch_names + ' was ' + first_name + "'s "
        if depth == 1:
            ch_names = ch_names + children[0].get_name_as_a_child()
        else:
            ch_names = ch_names + children[0].get_name_as_a_grandchild()
    elif len(children) > 1:
        ch_names = ch_names + ' were ' + first_name + "'s" 
        if depth == 1:
            ch_names = ch_names + " children"
        else:
            ch_names = ch_names + " grandchildren"
    return ch_names

class Dataset:
    def __init__(self):
        self.context_me = ""
        self.context_FDR = ""
        self.context_SDR = ""

        self.question_me = []
        self.question_me_dates = []
        self.question_me_places = []
        self.question_me_occupation = []

        self.question_FDR_me = []
        self.question_FDR_me_dates = []
        self.question_FDR_me_places = []
        self.question_FDR_me_occupation = []

        self.question_FDR = []
        self.question_FDR_dates = []
        self.question_FDR_places = []
        self.question_FDR_occupation = []


        self.question_SDR_me = []
        self.question_SDR_me_dates = []
        self.question_SDR_me_places = []
        self.question_SDR_me_occupation = []

        self.question_SDR_FDR = []
        self.question_SDR_FDR_dates = []
        self.question_SDR_FDR_places = []
        self.question_SDR_FDR_occupation = []

        self.question_SDR=[]
        self.question_SDR_dates = []
        self.question_SDR_places = []
        self.question_SDR_occupation = []

class ParsedPerson:
    
    def __init__(self,file_name,element,gedcom_parser):
        self.ged_element = element
        self.ged_id = get_string(element.get_pointer())
        self.file_name = file_name
        self.full_id = self.file_name + '_' + get_string(self.ged_id)
        try:
            self.first_name = capital_word(get_string(element.get_name()[0]))
        except:
            self.first_name = ''

        try:
            self.last_name = capital_word(get_string(element.get_name()[1]))
        except:
            self.last_name = ''

        try:
            self.is_deceased = element.is_deceased()
        except:
            self.is_deceased = None

        try:
            self.gender = get_string(element.get_gender())
        except:
            self.gender = None

        try:
            self.birth_date = get_string(element.get_birth_data()[0])
            if self.birth_date == '-1':
                self.birth_date = ''
        except:
            self.birth_date = ''

        try:
            self.birth_year = str(element.get_birth_year())
            if self.birth_year == '-1':
                self.birth_year = ''
        except:
            self.birth_year = ''

        try:
            self.death_year = str(element.get_death_year())
            if self.death_year == '-1':
                self.death_year = ''
        except:
            self.death_year = ''

        try:
            self.birth_place = get_string(element.get_birth_data()[1])
        except:
            self.birth_place = ''

        try:
            self.death_date = get_string(element.get_death_data()[0])
            if self.death_date == '-1':
                self.death_date = ''
        except:
            self.death_date = ''

        try:
            self.death_place = get_string(element.get_death_data()[1])
        except:
            self.death_place = ''

        try:
            self.burial_date = get_string(element.get_burial_data()[0])
            if self.burial_date == '-1':
                self.burial_date = ''
        except:
            self.burial_date = ''

        try:
            self.burial_place = get_string(element.get_burial_data()[1])
        except:
            self.burial_place = ''

        try:
            self.occupation = get_string(element.get_occupation())
        except:
            self.occupation = ''
        
        self.notes =''
        self.spouses = []
        self.children = []
        self.parents = []
        self.siblings = []
        person_cache[self.full_id] = self

    def is_child_in_family(self,family):
        family_id = family.get_pointer()
        for f in gedcom_parser.get_families(self.ged_element,gedcom.tags.GEDCOM_TAG_FAMILY_CHILD):
            if f.get_pointer() == family_id:
                return True
        return False

    def is_parent_in_family(self,family):
        family_id = family.get_pointer()
        for f in gedcom_parser.get_families(self.ged_element,gedcom.tags.GEDCOM_TAG_FAMILY_SPOUSE):
            if f.get_pointer() == family_id:
                return True
        return False

    def set_children_and_parents(self,file_name,element,gedcom_parser):
        try:
        #if 1==1:
            self.spouses = []
            self.children = []
            self.parents = []
            self.siblings = []
            for family in gedcom_parser.get_families(element,gedcom.tags.GEDCOM_TAG_FAMILY_SPOUSE):
                try:
                #if 1==1:
                    #self.print_debug('family as spouse: '+ family.get_pointer() )
                    spouses = gedcom_parser.get_family_members(family)
                    selected_spouse = ''
                    spouse_obj = None
                    try:
                    #if 1==1:
                        
                        for spouse in spouses:
                            spouse_id = spouse.get_pointer()
                            spouse_cache_id = self.file_name + '_' + spouse_id
                            if spouse_id != self.ged_id and  spouse_cache_id in person_cache:
                                spouse_obj_to_check = person_cache[spouse_cache_id]
                                is_parent = spouse_obj_to_check.is_parent_in_family(family)
                                #self.print_debug('spouse_id: '+ spouse_id + ' is_parent: ' + str(is_parent))
                                if is_parent == False:
                                    spouse_obj = spouse_obj_to_check
                                    break
                    except:
                        pass
                    
                    date = ''
                    place = ''
                    try:
                    #if 1==1:
                        for family_data in family.get_child_elements():
                            if family_data.get_tag() == gedcom.tags.GEDCOM_TAG_MARRIAGE:
                                for marriage_data in family_data.get_child_elements():
                                    if marriage_data.get_tag() == gedcom.tags.GEDCOM_TAG_DATE:
                                        date = marriage_data.get_value()
                                    if marriage_data.get_tag() == gedcom.tags.GEDCOM_TAG_PLACE:
                                        place = marriage_data.get_value()
                                break
                    except:
                        pass
                    
                    if spouse_obj is not None or len(date) > 0 or len(place) > 0:
                        self.spouses.append([spouse_obj,date,place])
                    
                    try:
                    #if 1==1:
                        for c in gedcom_parser.get_family_members(family):
                            if self.ged_id != c.get_pointer():
                                c_cache_key = self.file_name + '_' + c.get_pointer()
                                if c_cache_key in person_cache:
                                    child_obj = person_cache[c_cache_key]
                                    is_child = child_obj.is_child_in_family(family)
                                    #self.print_debug('family member: '+ c.get_pointer()  + ' is_child: ' + str(is_child))
                                    if is_child == True and child_obj not in self.children:
                                        self.children.append(child_obj)
                    except:
                        pass
                except:
                    pass


            for family in gedcom_parser.get_families(element,gedcom.tags.GEDCOM_TAG_FAMILY_CHILD):
                try:
                #if 1==1:
                    #self.print_debug('family as child: '+ family.get_pointer())
                    fms = gedcom_parser.get_family_members(family)
                    for s in fms:
                        if self.ged_id != s.get_pointer():
                            s_cache_key = self.file_name + '_' + s.get_pointer()
                            if s_cache_key in person_cache:
                                person_obj = person_cache[s_cache_key]
                                is_child = person_obj.is_child_in_family(family)
                                is_parent = person_obj.is_parent_in_family(family)
                                #self.print_debug('family member: '+ s.get_pointer()  + ' is_child: ' + str(is_child) + ' is parent: ' + str(is_parent) )                                    
                                if is_child == True:
                                    if person_obj not in self.siblings:
                                        self.siblings.append(person_obj)
                                elif is_parent == True:
                                    if person_obj not in self.parents:
                                        self.parents.append(person_obj)
                                #else:
                                    #self.print_debug('family member: '+ s.get_pointer()  + ' not a child or parent! ' )
                except:
                    pass
        except:
            pass

    def set_notes(self, val):
        self.notes = get_string(val)
    def get_name(self):
        name = ''
        sep=''
        if len(self.first_name) > 0:
            name = self.first_name
            sep = ' '

        if len(self.last_name) >0:
            name = name + sep + self.last_name
        return capital_word(name)

    def get_name_as_a_sibling(self):
        if self.gender.lower() == 'f':
            return ' sister '
        if self.gender.lower() == 'm':
            return ' brother '
        return ' sibling '

    def get_name_as_a_parent(self):
        if self.gender.lower() == 'f':
            return ' mother '
        if self.gender.lower() == 'm':
            return ' father '
        return ' parent '

    def get_name_as_a_grandparent(self):
        if self.gender.lower() == 'f':
            return ' grandmother '
        if self.gender.lower() == 'm':
            return ' grandfather '
        return ' grandparent '

    def get_name_as_a_child(self):
        if self.gender.lower() == 'f':
            return ' daughter '
        if self.gender.lower() == 'm':
            return ' son '
        return ' child '

    def get_name_as_a_grandchild(self):
        if self.gender.lower() == 'f':
            return ' granddaughter '
        if self.gender.lower() == 'm':
            return ' grandson '
        return ' grandchild '

    def set_occupation_qas(self,occupation,name,c,qas):
        if len(occupation) > 0:
            answers = create_value_answers(occupation, c)
            if len(answers)>0:
                qas.append(create_qa('What is ' +name +"s occupation?",answers))
                qas.append(create_qa('In what ' +name +" worked?",answers))
                qas.append(create_qa('What was the profession of ' +name +"?",answers))

    def set_birth_year_qas(self,year,name,c,qas):
        if len(year) > 0:
            answers = create_value_answers(year, c)
            if len(answers)>0:
                qas.append(create_qa('When did ' +name +" was born?",answers))
                qas.append(create_qa('When is ' +name +"'s birth date?",answers))
                qas.append(create_qa('When is ' +name +"'s birthday?",answers))

    def set_birth_place_qas(self,place,name,c,qas):
        if len(place) > 0:
            answers = create_value_answers(place, c)
            if len(answers)>0:
                qas.append(create_qa('Where did ' +name +" was born?",answers))

    def set_death_place_qas(self,place,name,c,qas):
        if len(place) > 0:
            answers = create_value_answers(place, c)
            if len(answers)>0:
                qas.append(create_qa('Where did ' +name +" died?",answers))

    def set_burial_place_qas(self,place,name,c,qas):
        if len(place) > 0:
            answers = create_value_answers(place, c)
            if len(answers)>0:
                qas.append(create_qa('Where did ' +name +" buried?",answers))
                qas.append(create_qa('Where did ' +name +" was buried?",answers))
                qas.append(create_qa('Where did ' +name +" is buried?",answers))

    def set_death_year_qas(self,year,name,c,qas):
        if len(year) > 0:
            answers = create_value_answers(year, c)
            if len(answers)>0:
                qas.append(create_qa('When did ' +name +" was died?",answers))

    def get_name_as_a_spouse(self):
        if self.gender is not None and self.gender.lower() == 'f':
            return 'wife'
        if self.gender is not None and self.gender.lower() == 'm':
            return 'husbend' 
        return 'spouse'
        

    def get_context_impl(self, name, include_spouse, include_dates, include_places, include_occupation, include_gender):
                
        sentences = []
        is_female = False

        if include_gender == True:
            if len(self.gender) > 0:
                if self.gender.lower() == 'f':
                    sentences.append(name + ' was a female.')
                    is_female = True
                elif self.gender.lower() == 'm':
                    sentences.append(name + ' was a male. ')

        if include_dates == True or include_places == True:
            if (len(self.birth_year) > 0 or len (self.birth_place) > 0):
                c = name + ' was born '
                if len(self.birth_year) > 0 and include_dates == True:
                    c = c + ' in ' + self.birth_year
                if len(self.birth_place) > 0 and include_places == True:
                    c = c + ' on ' + self.birth_place
                sentences.append(c + ".")

            if (self.is_deceased is not None and self.is_deceased == True) or len(self.death_year) > 0 or len (self.death_place) > 0 or len (self.burial_place) > 0:
                c = name + ' died '
                if len(self.death_year) > 0 and include_dates == True:
                    c = c + ' in ' + self.death_year

                if len(self.death_place) > 0 and include_places == True:
                    c = c + ' on ' + self.death_place

                sentences.append(c + ". ")

                if len (self.burial_place) > 0 and include_places == True:
                    sentences.append(name + ' was buried on ' + self.burial_place + '. ')

        if len(self.spouses) > 0 and include_spouse == True:
            sentences.append(name + ' had ' + str(len(self.spouses)) + ' spouses.')
            if is_female:
                sentences.append(name + ' had ' + str(len(self.spouses)) + ' husbands.')
            else:
                sentences.append(name + ' had ' + str(len(self.spouses)) + ' wifes.')

            for spouse_tuple in self.spouses:
                c = name + ' married'
                if spouse_tuple[0] is not None:
                    c = c + ' to ' + spouse_tuple[0].get_name() + ' '
                    if len(spouse_tuple[1]) > 0 and include_dates == True:
                        c = c + ' in ' + spouse_tuple[1] + ' '
                    if len(spouse_tuple[2]) > 0 and include_places == True:
                        c = c + ' on ' + spouse_tuple[2] + ' '
                    sentences.append(c+ '. ')
                    sentences.append(spouse_tuple[0].get_name() + ' is ' + self.first_name + "'s " + spouse_tuple[0].get_name_as_a_spouse() + '. ')

        if len(self.occupation) > 0 and include_occupation == True:
            sentences.append(name + ' was working as a ' + self.occupation + '. ')

            
        return sentences

    def set_common_qas(self,names,c,dates_qlst, places_qlst, occupation_qlst):
        for name in names:                
            if len(self.birth_year) > 0:
                self.set_death_year_qas(self.death_year,name,c,dates_qlst)

            if len(self.death_year) > 0:
                self.set_death_year_qas(self.death_place,name,c,dates_qlst)

            if len(self.birth_place) > 0:
                self.set_birth_place_qas(self.birth_place,name,c,places_qlst)

            if len(self.death_place) > 0:
                self.set_death_place_qas(self.death_place,name,c,places_qlst)

            if len(self.burial_place) > 0:
                self.set_burial_place_qas(self.burial_place,name,c,places_qlst)

            if len(self.occupation) > 0:
                self.set_occupation_qas(self.occupation,name,c,occupation_qlst)
                
    def get_context_text(self, depth, include_spouse, include_dates, include_places, include_occupation, include_gender):
        c,p_names,ch_names,sib_names,gp_names,gc_names = self.get_context_text_and_fregments(depth, include_spouse, include_dates, include_places, include_occupation, include_gender)
        return c

    def get_context_text_and_fregments(self, depth, include_spouse, include_dates, include_places, include_occupation, include_gender):
        name = self.get_name()
        
        sentences = []

        sentences.extend(self.get_context_impl(name, include_spouse,include_dates, include_places, include_occupation, include_gender))

        p_names = ''
        ch_names = ''
        sib_names = ''
        gp_names = ''
        gc_names = ''

        if depth > 1:

            p_names = get_parents(self.parents, self.first_name, 1)

            if len(p_names) > 0:
                sentences.append(p_names + '. ')
                sentences.append(name + ' had '+ str(len(self.parents)) +' parents. ')
                all_grand_parents = []
                for p in self.parents:
                    pname = self.first_name + "'s " + p.get_name_as_a_parent() + ' (' + p.get_name() + ')'
                    sentences.extend(p.get_context_impl(pname, include_spouse,include_dates, include_places, include_occupation, include_gender))
                    if depth > 2:
                        t_gp_names = get_parents(p.parents, self.first_name, 2)
                        if len(t_gp_names) > 0:
                            sentences.append(pname + ' had '+ str(len(p.parents)) +' parents. ')
                            all_grand_parents.extend(p.parents)
                            for gp in p.parents:
                                sentences.extend(gp.get_context_impl(self.first_name + "'s " + gp.get_name_as_a_grandparent() + ' (' + gp.get_name() + ')', False,include_dates, include_places, include_occupation, include_gender))
                
                if len(all_grand_parents) > 0:
                    gp_names = get_parents(all_grand_parents,  self.first_name, 2)
                    sentences.append(name + ' had '+ str(len(all_grand_parents)) +' grandparents. ')
                    if len(gp_names) > 0:
                        sentences.append(gp_names + '. ')


            ch_names = get_children(self.children, self.first_name, 1)
            
            if len(ch_names) > 0:
                sentences.append(ch_names + '. ')
                sentences.append(name + ' had '+ str(len(self.children)) +' children. ')
                all_grand_children = []
                for ch in self.children:
                    cname = self.first_name + "'s " + ch.get_name_as_a_child() + ' (' + ch.get_name() + ')'
                    sentences.extend(ch.get_context_impl(cname, include_spouse,include_dates, include_places, include_occupation, include_gender))
                    if depth > 2:
                        t_gc_names = get_children(ch.children,  self.first_name, 2)
                        if len(t_gc_names) > 0:
                            sentences.append(cname + ' had '+ str(len(ch.children)) +' children. ')
                            all_grand_children.extend(ch.children)
                            for gch in ch.children:
                                sentences.extend(gch.get_context_impl(self.first_name + "'s " + gch.get_name_as_a_grandchild() + ' (' + gch.get_name() + ')', False,include_dates, include_places, include_occupation, include_gender))
                
                if len(all_grand_children) > 0:
                    gc_names = get_children(all_grand_children,  self.first_name, 2)
                    sentences.append(name + ' had '+ str(len(all_grand_children)) +' grandchildren. ')
                    if len(gc_names) > 0:
                        sentences.append(gc_names + '. ')

            if depth > 2:
                sep = ''
                for sib in self.siblings:
                    sib_names = sib_names + sep + sib.get_name()
                    sep = ' and '
                    sentences.append( sib.get_name() + ' had '+ str(len(self.siblings)) +' siblings. ')
                    sentences.append( sib.get_name() + ' had '+ str(len(self.siblings)) +' brothers and sisters. ')

                if len(self.siblings) >0:
                    sentences.append( name + ' had '+ str(len(self.siblings)) +' siblings. ')
                    sentences.append( name + ' had '+ str(len(self.siblings)) +' brothers and sisters. ')
                    if len(self.siblings) == 1:
                        sib_names = sib_names + ' was ' + self.first_name + "'s " + self.siblings[0].get_name_as_a_sibling()
                    elif len(self.siblings) > 1:
                        sib_names = sib_names + ' were ' + self.first_name + "'s siblings"

                    sentences.append(sib_names + '. ')
                    for sib in self.siblings:
                        sentences.extend(sib.get_context_impl(self.first_name + "'s " + sib.get_name_as_a_sibling() + ' (' + sib.get_name() + ')',False, include_dates, include_places, include_occupation, include_gender))

        
        noraml_sentences = []

        for s in sentences:
            s = get_string(s)
            s = s.strip()
            s = re.sub(' +', ' ', s)
            noraml_sentences.append(s)
        
        facts = noraml_sentences
        random.shuffle(facts)

        c = ' '.join(facts)
        c = re.sub(' +', ' ', c)
        c = get_string(c)

        return c,p_names,ch_names,sib_names,gp_names,gc_names

    def add_me_questions(self, name, c, qlst, dates_qlst,places_qlst,occupation_qlst):
        if len(self.first_name) > 0:
            answers = create_value_answers(name, c)
            if len(answers)>0:
                qlst.append(create_qa('What is ' + self.first_name +' full name?',answers))

        if len(self.last_name) > 0 and len(self.first_name) > 0:
            
            answers = create_value_answers(self.last_name, c)
            if len(answers)>0:
                qlst.append(create_qa('What is ' + self.first_name +' last name?',answers))

            answers = create_value_answers(self.first_name, c)
            if len(answers)>0:
                prefix = ''
                if self.gender is not None and self.gender.lower() == 'f':
                    prefix = 'Miss'
                if self.gender is not None and self.gender.lower() == 'm':
                    prefix = 'Mr'

                qlst.append(create_qa('What is ' + prefix+ ' ' + self.last_name +' first name?',answers))

        self.set_common_qas([name],c,dates_qlst,places_qlst,occupation_qlst)

    def add_FDR_questions(self,name,isSDR,c,p_names,gp_names,ch_names, gc_names, qlst,dates_qlst,places_qlst,occupation_qlst, dataset):
        if len(p_names) > 0:
            answers = create_value_answers(str(len(self.parents)) + ' parents.', c)
            if len(answers)>0:
                qlst.append(create_qa('How many parents ' + name+ " had?",answers))
            answers = create_value_answers(p_names, c)
            if len(answers)>0:
                qlst.append(create_qa('Who are ' +name +"s parents?",answers))
                qlst.append(create_qa('What are ' +name +"s parents names?",answers))

            if isSDR==True and len(gp_names) > 0:
                answers = create_value_answers(gp_names, dataset.context_SDR)
                if len(answers)>0:
                    dataset.question_SDR.append(create_qa('Who are ' +name +"s grandparents?",answers))
                    dataset.question_SDR.append(create_qa('What are ' +name +"s grandparents names?",answers))
            gpcount = 0
            for p in self.parents:
                gpcount = gpcount + 1
                relative_name = name +"s " + p.get_name_as_a_parent() 
                answers = create_value_answers(p.get_name(), c)
                if len(answers)>0:
                    qlst.append(create_qa('Who is ' +relative_name + "?",answers))
                    qlst.append(create_qa('What is ' +relative_name + " name?",answers))

                answers = create_value_answers(name +"s " + p.get_name_as_a_parent(), c)
                if len(answers) > 0:
                    qlst.append(create_qa('Who is ' + p.get_name() + "?",answers))
                    qlst.append(create_qa('Who is ' + p.first_name + "?",answers))

                p.set_common_qas([relative_name,p.get_name()],c,dates_qlst,places_qlst,occupation_qlst)

                if isSDR==True:
                    for gp in p.parents:
                        gpcount = gpcount + 1
                        relative_name = name +"s " + gp.get_name_as_a_grandparent() 
                        answers = create_value_answers(gp.get_name(), dataset.context_SDR)
                        if len(answers)>0:
                            dataset.question_SDR.append(create_qa('Who is ' +relative_name + "?",answers))
                            dataset.question_SDR.append(create_qa('What is ' +relative_name + " name?",answers))

                        answers = create_value_answers(name +"s " + gp.get_name_as_a_grandparent(), dataset.context_SDR)
                        if len(answers) > 0:
                            dataset.question_SDR.append(create_qa('Who is ' + gp.get_name() + "?",answers))
                            dataset.question_SDR.append(create_qa('Who is ' + gp.first_name + "?",answers))

                        gp.set_common_qas([relative_name,gp.get_name()],dataset.context_SDR,dataset.question_SDR_dates,dataset.question_SDR_places,dataset.question_SDR_occupation)
                    
                    answers = create_value_answers(str(gpcount) + ' grandparents.',  dataset.context_SDR)
                    if len(answers)>0:
                        dataset.question_SDR.append(create_qa('How many grandparents ' + name+ " had?",answers))

        if len(ch_names) > 0:
            answers = create_value_answers(str(len(self.children)) + ' children.', c)
            if len(answers)>0:
                qlst.append(create_qa('How many children ' + name+ " had?",answers))
            answers = create_value_answers(ch_names, c)
            if len(answers)>0:
                qlst.append(create_qa('Who are ' +name +"s children?",answers))
                qlst.append(create_qa('What are ' +name +"s children names?",answers))

            if isSDR==True and len(gc_names) > 0:
                    answers = create_value_answers(gc_names, dataset.context_SDR)
                    if len(answers)>0:
                        dataset.question_SDR.append(create_qa('Who are ' +name +"s grandchildren?",answers))
                        dataset.question_SDR.append(create_qa('What are ' +name +"s grandchildren names?",answers))
            gccount = 0
            for ch in self.children:
                gccount = gccount + 1
                answers = create_value_answers(ch.get_name(), c)
                relative_name = name +"s " + ch.get_name_as_a_child()

                if len(answers) > 0:
                    qlst.append(create_qa('Who is ' + relative_name + "?",answers))
                    qlst.append(create_qa('What is ' + relative_name + " name?",answers))

                answers = create_value_answers(name +"s " + ch.get_name_as_a_child(),c)
                if len(answers) > 0:
                    qlst.append(create_qa('Who is ' + ch.get_name() + "?",answers))
                    qlst.append(create_qa('Who is ' + ch.first_name + "?",answers))
                
                ch.set_common_qas([relative_name,ch.get_name()],c,dates_qlst,places_qlst,occupation_qlst)

                if isSDR==True:
                    for gch in ch.children:
                        gccount = gccount + 1
                        answers = create_value_answers(gch.get_name(), dataset.context_SDR)
                        relative_name = name +"s " + gch.get_name_as_a_grandchild()

                        if len(answers) > 0:
                            dataset.question_SDR.append(create_qa('Who is ' + relative_name + "?",answers))
                            dataset.question_SDR.append(create_qa('What is ' + relative_name + " name?",answers))

                        answers = create_value_answers(name +"s " + gch.get_name_as_a_grandchild(), dataset.context_SDR)
                        if len(answers) > 0:
                            dataset.question_SDR.append(create_qa('Who is ' + gch.get_name() + "?",answers))
                            dataset.question_SDR.append(create_qa('Who is ' + gch.first_name + "?",answers))

                        gch.set_common_qas([relative_name,gch.get_name()],dataset.context_SDR,dataset.question_SDR_dates,dataset.question_SDR_places,dataset.question_SDR_occupation)
                    
                    answers = create_value_answers(str(gccount) + ' grandchildren.',  dataset.context_SDR)
                    if len(answers)>0:
                        dataset.question_SDR.append(create_qa('How many grandchildren ' + name+ " had?",answers))


    def get_dataset(self):

        dataset = Dataset()

        me_txt,me_p_names,me_ch_names,me_sib_names,me_gp_names,me_gc_names = self.get_context_text_and_fregments(1,False,True,True,True,True)
        dataset.context_me = me_txt

        fdr_txt,fdr_p_names,fdr_ch_names,fdr_sib_names,fdr_gp_names,fdr_gc_names = self.get_context_text_and_fregments(2,False,True,True,True,True)
        dataset.context_FDR = fdr_txt
        
        sdr_txt,sdr_p_names,sdr_ch_names,sdr_sib_names,sdr_gp_names,sdr_gc_names = self.get_context_text_and_fregments(3,True,True,True,True,True)
        dataset.context_SDR = sdr_txt

        name = self.get_name()

        self.add_me_questions(name, dataset.context_me, dataset.question_me, dataset.question_me_dates,dataset.question_me_places,dataset.question_me_occupation)
        self.add_me_questions(name, dataset.context_FDR, dataset.question_FDR_me, dataset.question_FDR_me_dates,dataset.question_FDR_me_places,dataset.question_FDR_me_occupation)
        self.add_me_questions(name, dataset.context_SDR, dataset.question_SDR_me, dataset.question_SDR_me_dates,dataset.question_SDR_me_places,dataset.question_SDR_me_occupation)
        
        self.add_FDR_questions(name, False, dataset.context_FDR, fdr_p_names, fdr_gp_names,fdr_ch_names,fdr_gc_names, dataset.question_FDR, dataset.question_FDR_dates,dataset.question_FDR_places,dataset.question_FDR_occupation,dataset)
        self.add_FDR_questions(name, True, dataset.context_SDR,  sdr_p_names, sdr_gp_names,sdr_ch_names,sdr_gc_names,dataset.question_SDR_FDR, dataset.question_SDR_FDR_dates,dataset.question_SDR_FDR_places,dataset.question_SDR_FDR_occupation,dataset)

        
        if len(sdr_sib_names) > 0:
            answers = create_value_answers(str(len(self.siblings)) + ' siblings.', dataset.context_SDR)
            if len(answers)>0:
                dataset.question_SDR.append(create_qa('How many siblings ' + name+ " had?",answers))
                dataset.question_SDR.append(create_qa('How many brothers and sisters ' + name+ " had?",answers))
            answers = create_value_answers(sdr_sib_names, dataset.context_SDR)
            if len(answers)>0:
                dataset.question_SDR.append(create_qa('Who are ' +name +"s siblings?",answers))
                dataset.question_SDR.append(create_qa('What are ' +name +"s siblings name?",answers))
            for sib in self.siblings:
                answers = create_value_answers(sib.get_name(), dataset.context_SDR)
                relative_name = name +"s " + sib.get_name_as_a_sibling()

                if len(answers) > 0:
                    dataset.question_SDR.append(create_qa('Who is ' + relative_name + "?",answers))
                    dataset.question_SDR.append(create_qa('What is ' + relative_name + " name?",answers))

                answers = create_value_answers(name +"s " + sib.get_name_as_a_sibling(), dataset.context_SDR)
                if len(answers) > 0:
                    dataset.question_SDR.append(create_qa('Who is ' + sib.get_name() + "?",answers))
                    dataset.question_SDR.append(create_qa('Who is ' + sib.first_name + "?",answers))
                
                sib.set_common_qas([relative_name,sib.get_name()],dataset.context_SDR,dataset.question_SDR_dates,dataset.question_SDR_places,dataset.question_SDR_occupation)

        if len(self.spouses) > 0:
            
            answers = create_value_answers(str(len(self.spouses)) + ' spouses.', dataset.context_SDR)
            if len(answers)>0:
                dataset.question_SDR.append(create_qa('How many spouses ' + name+ " had?",answers))
                dataset.question_SDR.append(create_qa('How many life partners ' + name+ " had?",answers))
                dataset.question_SDR.append(create_qa('How many ' + self.get_name_as_a_spouse() + 's ' + name+ " had?",answers))

            for spouse_tuple in self.spouses:
                relative_name1 = ''
                relative_name2 = name +"s spouse"
                relative_name3 = name +"s life partner"
                if spouse_tuple[0] is not None:
                    relative_name1 = name +"s " + spouse_tuple[0].get_name_as_a_spouse()
                    answers = create_value_answers(spouse_tuple[0].get_name(), dataset.context_SDR)
                    if len(answers)>0:
                        dataset.question_SDR.append(create_qa('Who is ' + relative_name1+ "?",answers))
                        dataset.question_SDR.append(create_qa('Who is ' +relative_name2+"?",answers))
                        dataset.question_SDR.append(create_qa('Who is ' +relative_name3+"?",answers))
                        dataset.question_SDR.append(create_qa('What is ' + relative_name1+ " name?",answers))
                        dataset.question_SDR.append(create_qa('What is ' +relative_name2+" name?",answers))
                        dataset.question_SDR.append(create_qa('What is ' +relative_name3+" name?",answers))

                if len(spouse_tuple[1]) > 0:
                    answers = create_value_answers(spouse_tuple[1], dataset.context_SDR)
                    if len(answers)>0:
                        dataset.question_SDR_dates.append(create_qa('When did ' +name +" got married?",answers))
                if len(spouse_tuple[2]) > 0:
                    answers = create_value_answers(spouse_tuple[2], dataset.context_SDR)
                    if len(answers)>0:
                        dataset.question_SDR_places.append(create_qa('Where did ' +name +" got married?",answers))

        return dataset

create_train_dataset = True
create_test_dataset = False

test_folder = output_folder + 'test/'
def append_data(data, name, context, lst_qas, ):
    if len(context) > 0 and len(lst_qas) > 0:   
        d = {
        "title":name,
        "paragraphs":[]
        }
        d["paragraphs"].append( {
            "qas":lst_qas,
            "context" :context
        })
        data.append(d)

if create_train_dataset == True:
    texts = []
    quastions = []

    files_count = 0
    total_files = 0
    total_parsed_files = 0

    os.chdir(gedcom_folder)
    lst_files = glob.glob("*.ged")

    print ('start parsing - ' + str(datetime.datetime.now()))
    for file_name in tqdm(lst_files):
    #if 1==1:
        #file_name = '5845 Abramson260303newtree.ged'
        try:
        #if 1==1:           
            total_files = total_files + 1
            gedcom_parser = Parser()
            gedcom_parser.parse_file(gedcom_folder + file_name, False)

            all_elements = gedcom_parser.get_element_list()
            
            total_parsed_files = total_parsed_files + 1
            indv_count = 0

            for element in all_elements:
                if isinstance(element, IndividualElement):
                    indv_count = indv_count + 1

            if indv_count > 100 and indv_count < 2000:

                for element in all_elements:
                    if isinstance(element, IndividualElement):
                        cache_id = file_name + '_' + element.get_pointer()
                        a = ParsedPerson(file_name, element, gedcom_parser) #will add itself to person_cache
                                        
                for element in all_elements:
                    if isinstance(element, IndividualElement):
                        cache_id = file_name + '_' + element.get_pointer()
                        if cache_id in person_cache:
                            person_cache[cache_id].set_children_and_parents(file_name, element, gedcom_parser)
        except:
            pass

    print ('done parsing - ' + str(datetime.datetime.now()))
    print ('total files: ' + str(total_files))
    print ('total_parsed_files: ' + str(total_parsed_files))
    print ('total_ppl: ' + str(len(person_cache)))


    # SQuAd format
    # https://rajpurkar.github.io/SQuAD-explorer/explore/v2.0/dev/


    q_num = 0

    person_per_tree = {}
    for pid in person_cache:
        if person_cache[pid].file_name not in person_per_tree:
            person_per_tree[person_cache[pid].file_name] = []
        person_per_tree[person_cache[pid].file_name].append(person_cache[pid])

    train_folder = output_folder + 'train/'
    

    train_me_folder = train_folder + 'me/'
    train_FDR_folder = train_folder + 'fdr/'
    train_SDR_folder = train_folder + 'sdr/'


    folder = [output_folder,train_folder,test_folder,train_me_folder,train_FDR_folder,train_SDR_folder]

    for f in folder:
        if os.path.exists(f) == False:
            os.mkdir(f)

    q_num = 0

    

    for filename in tqdm(person_per_tree):    
        try:
        
            datas = {}
            datasets = {}
            #train datasets
            for person in person_per_tree[filename]:
                    
                dataset = person.get_dataset()
                datasets[person.full_id] = [person.get_name(), dataset]

                #me
                output_filename = train_me_folder + filename + 'ged_squad.json'

                if output_filename not in datas:
                    datas[output_filename] = []

                context = dataset.context_me
                lst_qas = []
                lst_qas.extend(dataset.question_me)
                lst_qas.extend(dataset.question_me_dates)
                lst_qas.extend(dataset.question_me_places)
                lst_qas.extend(dataset.question_me_occupation)          
                append_data(datas[output_filename], person.get_name(), context, lst_qas)
                q_num = q_num + len(lst_qas)

                #FDR
                output_filename = train_FDR_folder + filename + 'ged_squad.json'

                if output_filename not in datas:
                    datas[output_filename] = []

                context = dataset.context_FDR
                lst_qas = []
                lst_qas.extend(dataset.question_FDR_me)
                lst_qas.extend(dataset.question_FDR_me_dates)
                lst_qas.extend(dataset.question_FDR_me_places)
                lst_qas.extend(dataset.question_FDR_me_occupation)
                lst_qas.extend(dataset.question_FDR)
                lst_qas.extend(dataset.question_FDR_dates)
                lst_qas.extend(dataset.question_FDR_places)
                lst_qas.extend(dataset.question_FDR_occupation)
                append_data(datas[output_filename], person.get_name(), context, lst_qas)
                q_num = q_num + len(lst_qas)

                #SDR
                output_filename = train_SDR_folder + filename + 'ged_squad.json'

                if output_filename not in datas:
                    datas[output_filename] = []

                context = dataset.context_SDR
                lst_qas = []
                lst_qas.extend(dataset.question_SDR_me)
                lst_qas.extend(dataset.question_SDR_me_dates)
                lst_qas.extend(dataset.question_SDR_me_places)
                lst_qas.extend(dataset.question_SDR_me_occupation)
                lst_qas.extend(dataset.question_SDR_FDR)
                lst_qas.extend(dataset.question_SDR_FDR_dates)
                lst_qas.extend(dataset.question_SDR_FDR_places)
                lst_qas.extend(dataset.question_SDR_FDR_occupation)
                lst_qas.extend(dataset.question_SDR)
                lst_qas.extend(dataset.question_SDR_dates)
                lst_qas.extend(dataset.question_SDR_places)
                lst_qas.extend(dataset.question_SDR_occupation)
                append_data(datas[output_filename], person.get_name(), context, lst_qas)
                q_num = q_num + len(lst_qas)

            for output_filename in datas:
                if len(datas[output_filename]) > 0:
                    jsonObj = {
                        "version":"v2.0",
                        "data": datas[output_filename]
                        }
                    f = open(output_filename, "w")
                    f.write(json.dumps(jsonObj))
                    f.close()

            pickle.dump( datasets, open( test_folder + filename + 'dataset.p', "wb" ) )
        except:
            pass   

    print ('done writing json - ' + str(datetime.datetime.now()))
    print ('questions: ' + str(q_num))

def get_pred(folder):
    os.chdir(folder)
    f = []
    for filename in tqdm(glob.glob("*.json")):    
        f.append(filename)
    return f

def create_test_json_obj(test_folder_json, filename, q_type_name, datas, dataset, pid, lst_qas):
    dir = test_folder_json + q_type_name + '/'

    if os.path.exists(dir) == False:
        os.mkdir(dir)

    output_filename = dir +filename + 'ged_squad.' + '.json'

    if output_filename not in datas:
        datas[output_filename] = []

    context = dataset.context_SDR
    append_data(datas[output_filename], pid + '_'+q_type_name, context, lst_qas)


if create_test_dataset == True:
    train_folder = output_folder + 'train/'
    test_folder_json = test_folder + 'json/'

    predictn_me_folder = train_folder + 'me/predict/'
    predict_FDR_folder = train_folder + 'fdr/predict/'
    predict_SDR_folder = train_folder + 'sdr/predict/'

    me_pred_files = get_pred(predictn_me_folder)
    fdr_pred_files = get_pred(predict_FDR_folder)
    sdr_pred_files = get_pred(predict_SDR_folder)

    pred_files = []
    for file in me_pred_files:
        if file in fdr_pred_files:
            if file in sdr_pred_files:
                pred_files.append(file)

    for f in tqdm(pred_files):
        try:   
            filename = f.replace('ged_squad.json','')
            datas = {}
            datasets = pickle.load( open( test_folder + filename + 'dataset.p', "rb" ) )
            #train datasets
            for pid in datasets:
                dataset  = datasets[pid][1]

                #create_test_json_obj(test_folder_json, filename, 'me', datas, dataset, datasets[pid][0], dataset.question_SDR_me)
                #create_test_json_obj(test_folder_json, filename, 'me_dates', datas, dataset, datasets[pid][0], dataset.question_SDR_me_dates)
                #create_test_json_obj(test_folder_json, filename, 'me_places', datas, dataset, datasets[pid][0], dataset.question_SDR_me_places)
                #create_test_json_obj(test_folder_json, filename, 'me_occupation', datas, dataset, datasets[pid][0], dataset.question_SDR_me_occupation)
                #create_test_json_obj(test_folder_json, filename, 'FDR', datas, dataset, datasets[pid][0], dataset.question_SDR_FDR)
                #create_test_json_obj(test_folder_json, filename, 'FDR_dates', datas, dataset, datasets[pid][0], dataset.question_SDR_FDR_dates)
                #create_test_json_obj(test_folder_json, filename, 'FDR_places', datas, dataset, datasets[pid][0], dataset.question_SDR_FDR_places)
                #create_test_json_obj(test_folder_json, filename, 'FDR_occupation', datas, dataset, datasets[pid][0], dataset.question_SDR_FDR_occupation)
                #create_test_json_obj(test_folder_json, filename, 'SDR', datas, dataset, datasets[pid][0], dataset.question_SDR)
                #create_test_json_obj(test_folder_json, filename, 'SDR_dates', datas, dataset, datasets[pid][0], dataset.question_SDR_dates)
                #create_test_json_obj(test_folder_json, filename, 'SDR_places', datas, dataset, datasets[pid][0], dataset.question_SDR_places)
                #create_test_json_obj(test_folder_json, filename, 'SDR_occupation', datas, dataset, datasets[pid][0], dataset.question_SDR_occupation)

                lst = []
                lst.extend(dataset.question_SDR_me)
                lst.extend(dataset.question_SDR_me_dates)
                lst.extend(dataset.question_SDR_me_places)
                lst.extend(dataset.question_SDR_me_occupation)
                lst.extend(dataset.question_SDR_FDR)
                lst.extend(dataset.question_SDR_FDR_dates)
                lst.extend(dataset.question_SDR_FDR_places)
                lst.extend(dataset.question_SDR_FDR_occupation)
                lst.extend(dataset.question_SDR)
                lst.extend(dataset.question_SDR_dates)
                lst.extend(dataset.question_SDR_places)
                lst.extend(dataset.question_SDR_occupation)

                create_test_json_obj(test_folder_json, filename, 'all', datas, dataset, datasets[pid][0], lst)

            for output_filename in datas:
                if len(datas[output_filename]) > 0:
                    jsonObj = {
                        "version":"v2.0",
                        "data": datas[output_filename]
                        }
                    f = open(output_filename, "w")
                    f.write(json.dumps(jsonObj))
                    f.close()

        except:
            pass
