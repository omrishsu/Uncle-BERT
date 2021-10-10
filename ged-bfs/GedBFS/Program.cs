
// Toy example of the GEN-BFS (algorithm 1 in the paper)
// you should fit it to the gedcom parsing library that you use
using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace GedBFS
{
    class Program
    {
        // GEDCOM abstract object
        public abstract class GenObject
        {
            public string name { get; }

            public GenObject(string name)
            {
                this.name = name;
            }

            public override string ToString()
            {
                return name;
            }
        }
        
        // GEDCOM individual object
        public class Person : GenObject
        {
            public Person(string name) :base(name) { }

            List<Family> ParentInFamiliesList = new List<Family>();

            public List<Family> ParentInFamilies
            {
                get
                {
                    return ParentInFamiliesList;
                }
            }

            List<Family> ChildInFamiliesList = new List<Family>();
            public List<Family> ChildInFamilies
            {
                get
                {
                    return ChildInFamiliesList;
                }
            }

            public void AddFamily(Family p, bool isParent)
            {
                if (isParent)
                    ParentInFamiliesList.Add(p);
                else
                    ChildInFamiliesList.Add(p);

                p.AddPerson(this, isParent);
            }
        }

        // GEDCOM family object
        public class Family : GenObject
        {
            public Family(string name) : base(name) { }
          
            List<Person> ChildrenList = new List<Person>();

            public List<Person> Children
            {
                get
                {
                    return ChildrenList;
                }
            }

            List<Person> ParentList = new List<Person>();

            public List<Person> Parents
            {
                get
                {
                    return ParentList;
                }
            }

            public void AddPerson(Person p, bool isParent)
            {
                if (isParent)
                    ParentList.Add(p);
                else
                    ChildrenList.Add(p);
            }

        }

        public class BreadthFirstAlgorithm
        {
            // Toy example
            public Person BuildGraph()
            {
                var sp = new Person("SP");

                var f1 = new Family("F1");
                var f2 = new Family("F2");
                var f3 = new Family("F3");
                var f4 = new Family("F4");
                var f5 = new Family("F5");
                var f6 = new Family("F6");

                var p1 = new Person("P1");
                var p2 = new Person("P2");
                var p3 = new Person("P3");
                var p4 = new Person("P4");
                var p5 = new Person("P5");
                var p6 = new Person("P6");
                var p7 = new Person("P7");
                var p8 = new Person("P8");
                var p10 = new Person("P10");
                var p11 = new Person("P11");
                var p12 = new Person("P12");
                var p13 = new Person("P13");
                var p14 = new Person("P14");
                var p15 = new Person("P15");
                var p16 = new Person("P16");
                var p17 = new Person("P17");

                sp.AddFamily(f1, false);
                sp.AddFamily(f4, true);

                p1.AddFamily(f1, true);
                p1.AddFamily(f2, false);

                p2.AddFamily(f1, true);
                p2.AddFamily(f3, false);

                p3.AddFamily(f2, true);
                p4.AddFamily(f2, true);
                p5.AddFamily(f3, true);
                p6.AddFamily(f3, true);
                p7.AddFamily(f1, false);
                p8.AddFamily(f1, false);
                
                p10.AddFamily(f4, true);
                p11.AddFamily(f5, true);

                p12.AddFamily(f5, true);
                p12.AddFamily(f4, false);

                p13.AddFamily(f6, true);
                p13.AddFamily(f4, false);

                p14.AddFamily(f6, true);
                
                p15.AddFamily(f5, false);
                p16.AddFamily(f5, false);
                p17.AddFamily(f6, false);

                return sp;
            }
            
            // BFS algorithm
            public void Traverse(GenObject parent, int maxDepth)
            {
                var nodeQueue = new Queue<GenObject>();
                var S = new HashSet<GenObject>();
                nodeQueue.Enqueue(parent);
                S.Add(parent);

                var traverseOrder = new Queue<Tuple<int,GenObject>>();
                int currentDepth = 0,
                    elementsToDepthIncrease = 1,
                    nextElementsToDepthIncrease = 0;

                while (nodeQueue.Count > 0)
                {
                    var current = nodeQueue.Dequeue();
                    traverseOrder.Enqueue(new Tuple<int, GenObject>(currentDepth, current));
                    GenObject[] lstNearNodes = null;
                    if (current is Person)
                    {
                        lstNearNodes = ((Person)current).ChildInFamilies.Union(((Person)current).ParentInFamilies).ToArray();
                    }
                    else
                    {
                        lstNearNodes = ((Family)current).Children.Union(((Family)current).Parents).ToArray();
                    }

                    nextElementsToDepthIncrease += lstNearNodes.Where(n=> !S.Contains(n)).Count();
                    if (--elementsToDepthIncrease == 0)
                    {
                        if (++currentDepth > maxDepth) break;
                        elementsToDepthIncrease = nextElementsToDepthIncrease;
                        nextElementsToDepthIncrease = 0;
                    }
                    foreach (var emp in lstNearNodes)
                    {
                        if (!S.Contains(emp))
                        {
                            nodeQueue.Enqueue(emp);
                            S.Add(emp);
                        }
                    }
                }

                while (traverseOrder.Count > 0)
                {
                    var e = traverseOrder.Dequeue();
                    Console.WriteLine(e.Item1 + " - " + e.Item2.ToString());
                }
            }

            // GEN-BFS algorithm
            public Queue<Tuple<int, GenObject>> GenTraverse(GenObject parent, int maxDepth)
            {
                var nodeQueue = new Queue<GenObject>();
                var visited = new HashSet<GenObject>();
                var added = new HashSet<GenObject>();
                nodeQueue.Enqueue(parent);
                visited.Add(parent);

                var traverseOrder = new Queue<Tuple<int, GenObject>>();
                var currentDepth = 0;
                var elementsToDepthIncrease = 1;
                var nextElementsToDepthIncrease = 0;

                while (nodeQueue.Count > 0)
                {
                    var current = nodeQueue.Dequeue();
                    traverseOrder.Enqueue(new Tuple<int, GenObject>(currentDepth, current));
                    added.Add(current);
                    GenObject[] lstNearNodes = null;
                    var increaseCount = 0;

                    if (current is Person)
                    {
                        lstNearNodes = ((Person)current).ChildInFamilies.Union(((Person)current).ParentInFamilies).ToArray();
                        increaseCount = lstNearNodes.Where(n => !visited.Contains(n)).Count();
                    }
                    else
                    {
                        lstNearNodes = ((Family)current).Children.Union(((Family)current).Parents).ToArray();
                        increaseCount = lstNearNodes.Where(n => !visited.Contains(n)).Count();
                    }

                    nextElementsToDepthIncrease += increaseCount;
                    if (--elementsToDepthIncrease == 0)
                    {
                        if (current is Person)
                            if (++currentDepth > maxDepth)
                                break;
                        elementsToDepthIncrease = nextElementsToDepthIncrease;
                        nextElementsToDepthIncrease = 0;
                    }

                    foreach (var emp in lstNearNodes)
                    {
                        if (!visited.Contains(emp))
                        {
                            nodeQueue.Enqueue(emp);
                            visited.Add(emp);
                        }
                    }
                }

                var output = new Queue<Tuple<int, GenObject>>();
                while (traverseOrder.Count > 0)
                {
                    var e = traverseOrder.Dequeue();
                    output.Enqueue(e);
                    if (e.Item2 is Person)
                    {
                        foreach (var f in ((Person)e.Item2).ParentInFamilies)
                        {
                            foreach (var emp in ((Family)f).Parents)
                            {
                                if (!added.Contains(emp))
                                {
                                    output.Enqueue(new Tuple<int, GenObject>(e.Item1,emp));
                                }
                            }
                        }
                    }
                }

                return output;
            }
        }

        // Test
        static void Main(string[] args)
        {
            BreadthFirstAlgorithm b = new BreadthFirstAlgorithm();
            Person root = b.BuildGraph();
            Console.WriteLine("Traverse Graph\n------");
            //            b.Traverse(root, 5);

            //b.GenTraverse(root, 1);
            //Console.ReadLine();
            //return;

            for (int i = 0; i <= 5; i++)
            {
                Console.WriteLine("Depth: " + i);
                b.Traverse(root, i);
                Console.WriteLine("---------------");
                Console.WriteLine("---------------");
                Console.WriteLine("---------------");
                Console.WriteLine();
            }

            Console.WriteLine("---------------");
            Console.WriteLine("---------------");
            Console.WriteLine("---------------");
            Console.WriteLine("-----GEN------");
            Console.WriteLine("---------------");
            Console.WriteLine("---------------");
            Console.WriteLine("---------------");

            for (int i = 0; i <= 5; i++)
            {
                Console.WriteLine("Depth: " + i);
                var traverseOrder = b.GenTraverse(root, i);
                while (traverseOrder.Count > 0)
                {
                    var e= traverseOrder.Dequeue();
                    Console.WriteLine(e.Item1 + " - " + e.Item2.ToString());
                }
                Console.WriteLine("---------------");
                Console.WriteLine("---------------");
                Console.WriteLine("---------------");
                Console.WriteLine();
            }


            Console.ReadLine();
        }
    }
}
