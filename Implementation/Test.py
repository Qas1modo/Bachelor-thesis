import prov.model
from Generator import DocumentGenerator
from Search import Search
from typing import Tuple


class CaseGenerator:
    """
    Object generating documents representing cases from the text by calling the generator with specific input.
    """

    def __init__(self):
        self.all_cases()

    @staticmethod
    def basic_cases():
        # 1. case (Basic case without has provenance)
        DocumentGenerator([1, 2, 1, 2, 2],
                          [],
                          "@/1/1.txt")
        # 2. case (Basic case without interconnections of chains)
        DocumentGenerator([[(1, [], 2), (2, "@/2/2.txt/5")], (2, "@/2/2.txt/6"),
                           [(1, [], 2), (2, "@/2/1.txt/4")], (2, "@/2/2.txt/7")],
                          [],
                          "@/2/1.txt")
        DocumentGenerator([(2, "@/2/1.txt/2"), 2, (2, "@/2/3.txt/9"), (3, "@/2/3.txt/10")],
                          [],
                          "@/2/2.txt", start_id=5)
        DocumentGenerator([2, 3],
                          [],
                          "@/2/3.txt", start_id=9)
        # 3. case (Basic case with content and no interconnections)
        DocumentGenerator([[1, (3, "@/3/2.txt/7")], (1, "@/3/2.txt/6"), 4, [(1, [], [3]), (3, "@/3/2.txt/5")]],
                          [],
                          "@/3/1.txt")
        DocumentGenerator([[(3, "@/3/1.txt", [8]), (8, "@/3/1.txt/9")], (1, "@/3/2.txt/8"), 3, 2],
                          [],
                          "@/3/2.txt", start_id=5)

        # 4. case (Basic case with interconnections)
        DocumentGenerator([[(1, ["@/4/2.txt/5", "@/4/2.txt/6"], [3]), (3, "@/4/1.txt/2")],
                           [(1, [], [3]), (3, "@/4/2.txt/4")], (1, "@/4/2.txt/5")],
                          [],
                          "@/4/1.txt")
        DocumentGenerator([[(3, [], [1]), (1, "@/4/3.txt/7")], (1, "@/4/3.txt/8"), (1, "@/4/3.txt/7")],
                          [],
                          "@/4/2.txt", start_id=4)
        DocumentGenerator([1, 1],
                          [],
                          "@/4/3.txt", start_id=7)

        # 5. case (Basic case with interconnections and content)
        DocumentGenerator([[(1, "@/5/2.txt/6", 4), (4, ["@/5/1.txt/2", "@/5/1.txt/2"])], (4, "@/5/2.txt/6"),
                           [(1, "@/5/2.txt/5", 2), (2, ["@/5/2.txt/5"], [4]), (4, "@/5/1.txt/4")], 4],
                          [],
                          "@/5/1.txt")
        DocumentGenerator([[(1, "@/5/2.txt/7"), (2, "@/5/2.txt/8")], [1, (4, "@/5/2.txt/9")], 1,
                           [(1, "@/5/2.txt/7"), (1, "@/5/2.txt/10"), (2, "@/5/2.txt/9", 1)], 4, 1],
                          [],
                          "@/5/2.txt", start_id=5)

    @staticmethod
    def cases_with_cycles():
        # 6. case (Has provenance cycle)
        DocumentGenerator([(1, "@/6/2.txt/4"), (1, "@/6/2.txt/3")],
                          [],
                          "@/6/1.txt")
        DocumentGenerator([(1, "@/6/2.txt/5"), (1, "@/6/2.txt/5"), (1, "@/6/2.txt/3")],
                          [],
                          "@/6/2.txt", start_id=3)

        # 7. case (Special case of cycle)
        DocumentGenerator([(1, "@/7/1.txt/1")], [], "@/7/1.txt")

        # 8. case (Has provenance cycle with content)
        DocumentGenerator([[(1, "@/8/2.txt/2", [2]), (2, "@/8/2.txt/2")]],
                          [],
                          "@/8/1.txt")
        DocumentGenerator([[(1, "@/8/2.txt/3"), (2, "@/8/2.txt/3"), (3, "@/8/2.txt/4")],
                           [(1, "@/8/2.txt/2"), (2, [], 3), (3, "@/8/2.txt/2")], 3],
                          [],
                          "@/8/2.txt", start_id=2)

    @staticmethod
    def cases_with_integrity_validations():
        # 9.case (Integrity without interconnections of chains)
        DocumentGenerator([(1, ["@/9/2.txt/2", "@/9/2.txt/3"])],
                          [],
                          "@/9/1.txt")
        DocumentGenerator([(1, ["@/9/2.txt/6", "@/9/2.txt/4"]), (1, "@/9/2.txt/5"),
                           (1, ["@/9/2.txt/7", "@/9/2.txt/8"]), 1, 1, 1, 1],
                          [],
                          "@/9/2.txt", [2, 7], 2)
        # 10.case (Integrity with interconnections of chains)
        DocumentGenerator([(1, ["@/10/2.txt/2", "@/10/2.txt/3"])],
                          [],
                          "@/10/1.txt")
        DocumentGenerator([(1, ["@/10/2.txt/4", "@/10/2.txt/5"]), (1, "@/10/2.txt/5"), 1, 1],
                          [],
                          "@/10/2.txt", [2], 2)
        # 11.case (Integrity with interconnections of chains and content)
        DocumentGenerator([(1, "@/11/2.txt/3"), [(1, [], 2), (2, "@/11/2.txt/3")]],
                          [],
                          "@/11/1.txt", [2])
        DocumentGenerator([[(1, "@/11/2.txt/6"), (2, "@/11/2.txt/5"), 3], (3, "@/11/2.txt/3"), 2,
                           [(1, [], 3), (3, "@/11/2.txt/4")]],
                          [],
                          "@/11/2.txt", [6], 3)

    @staticmethod
    def cases_with_updates():
        # 12.case (Basic linear update)
        DocumentGenerator([2, 1],
                          [1, 2, (4, [1], (1, "@/12/2.txt/6"))],
                          "@/12/1.txt")
        DocumentGenerator([1],
                          [6, 7],
                          "@/12/2.txt", start_id=6)

        # 13.case (Basic update without entity in newer version)
        DocumentGenerator([1],
                          [(1, [1], [(1, [], [2]), (2, "@/13/2.txt/5")]), (2, [1, 2], 3)],
                          "@/13/1.txt")
        DocumentGenerator([1],
                          [(4, [], [2]), (5, [1]), (6, [2], [1])],
                          "@/13/2.txt", start_id=4)

        # 14.case (Basic update without entity)
        DocumentGenerator([(1, ["@/14/2.txt/3", "@/14/3.txt/6"])],
                          [],
                          "@/14/1.txt")
        DocumentGenerator([1],
                          [(2, [1], 2), (3, [2], 3)],
                          "@/14/2.txt", start_id=2)
        DocumentGenerator([1],
                          [(5, [1], 2), (6, [2], 1), (7, [1], 2)],
                          "@/14/3.txt", start_id=5)

    @staticmethod
    def updates_with_cycles():
        # 15.case (Backward reference into older version)
        DocumentGenerator([(1, "@/15/2.txt/4")],
                          [1, 2],
                          "@/15/1.txt")
        DocumentGenerator([(1, "@/15/2.txt/5"), (1, "@/15/1.txt/2")],
                          [],
                          "@/15/2.txt", start_id=4)
        # 16.case (Backward reference into older version with different entity)
        DocumentGenerator([1],
                          [(1, [1], 2), (2, [2], (1, "@/16/2.txt/5")),
                           (3, [1], (2, ["@/16/2.txt/5", "@/16/2.txt/6"]))],
                          "@/16/1.txt")
        DocumentGenerator([[(1, "@/16/1.txt/1", [2]), (2, "@/16/1.txt/1")], 2],
                          [],
                          "@/16/2.txt", start_id=5)
        # 17.case (Basic update with reference into newer version)
        DocumentGenerator([[(1, [], [2]), (2, "@/17/2.txt/4")], (1, "@/17/2.txt/3")],
                          [],
                          "@/17/1.txt")
        DocumentGenerator([(1, [], [2]), 2],
                          [(3, [1])],
                          "@/17/2.txt", start_id=3)

    @staticmethod
    def updates_with_verification():
        # 18.case (Invalid older version in update branch)
        DocumentGenerator([1],
                          [1, (2, [1], (1, "@/18/2.txt/5"))],
                          "@/18/1.txt", [1])
        DocumentGenerator([1],
                          [4, 5],
                          "@/18/2.txt", [4], 4)
        # 19.case (Invalid between older and newer version)
        DocumentGenerator([1],
                          [1, (2, [1], (1, "@/19/2.txt/4"))],
                          "@/19/1.txt", [2])
        DocumentGenerator([1],
                          [4, (5, [1], (1, "@/19/3.txt/7"))],
                          "@/19/2.txt", [5], 4)
        DocumentGenerator([1],
                          [7, 8],
                          "@/19/3.txt", [9], 7)
        # 20.case (Reference into invalid bundle with update)
        DocumentGenerator([1],
                          [(1, [1], (1, "@/20/2.txt/5")), 2],
                          "@/20/1.txt", [3])
        DocumentGenerator([1],
                          [4, (5, [1], (1, "@/20/3.txt/7"))],
                          "@/20/2.txt", [5], 4)
        DocumentGenerator([1],
                          [7, (8, [1], [2])],
                          "@/20/3.txt", [7, 8], 7)
        # 21.case (Multiple references into update branch with invalid bundle)
        DocumentGenerator([(1, "@/21/2.txt/3"), (1, "@/21/2.txt/5")],
                          [],
                          "@/21/1.txt")
        DocumentGenerator([1],
                          [3, 4],
                          "@/21/2.txt", [4], 3)

    @staticmethod
    def merge_cases():
        # 22.case (Merge of bundles)
        DocumentGenerator([2, 1, (1, "@/22/2.txt/8")],
                          [(1, [], (1, "@/22/2.txt/5")), ((2, 4), [1])],
                          "@/22/1.txt")
        DocumentGenerator([1, 1, 1, 1],
                          [5, (6, 9), (7, [1], 4), ((8, 10), [1], [2, 3]), ((9, 10), [1], 5)],
                          "@/22/2.txt", start_id=5)
        # 23.case (Merge with content and invalid bundles)
        DocumentGenerator([(1, "@/23/2.txt/8"), (1, "@/23/2.txt/3")],
                          [],
                          "@/23/1.txt")
        DocumentGenerator([1, 2, 2, (2, "@/23/2.txt/5")],
                          [(3, [1]), ((4, 7), []), (7, [2], 1), (8, [1], (1, [], [2])),
                           ((5, 9), [2], (2, "@/23/2.txt/6"))],
                          "@/23/2.txt", [7, 6], 3)

    @staticmethod
    def fork_cases():
        # 24.case (Fork of bundle with invalid bundles)
        DocumentGenerator([1],
                          [(1, [1], 2), (1, [1], (1, "@/24/2.txt/6")), (2, [], 1), 2],
                          "@/24/1.txt")
        DocumentGenerator([1],
                          [6, 6, (7, [1], 3), 7, 8, 7],
                          "@/24/2.txt", [6, 8, 10, 12], 6)
        # 25.case (Fork with predecessors with multiple newer bundles)
        DocumentGenerator([(1, "@/25/2.txt/5")],
                          [],
                          "@/25/1.txt")
        DocumentGenerator([[1, 2], [(1, "@/25/2.txt/2", [2]), (2, "@/25/2.txt/2")]],
                          [(2, [2]), (2, [2]), 4, (4, [1], 2), 7, (5, [1], (1, "@/25/2.txt/10")),
                           (7, [2], (1, "@/25/2.txt/3"))],
                          "@/25/2.txt", start_id=2)

    @staticmethod
    def updates_in_cycle():
        # 26.case (Document with updates in cycle)
        DocumentGenerator([1],
                          [(1, [1], 2), (2, [], (1, "@/26/2.txt/8")), 1],
                          "@/26/1.txt", [1])
        DocumentGenerator([1, 1],
                          [5, (6, 7), 7, 7, (9, 6)],
                          "@/26/2.txt", [9], 5)

    def all_cases(self):
        self.basic_cases()
        self.cases_with_cycles()
        self.cases_with_integrity_validations()
        self.cases_with_updates()
        self.updates_with_cycles()
        self.updates_with_verification()
        self.merge_cases()
        self.fork_cases()
        self.updates_in_cycle()


class ResultPrinter:
    """
    Starts generation of provenance documents representing cases and then run the search algorithm to test
     the output of separate cases and print result.
    """
    def __init__(self, regenerate: bool = True, automatic_test: bool = True):
        """
        Initializer of testing.

        :param regenerate: Bool which denotes if files with cases should be regenerated.
        :param automatic_test: Bool which denotes if automatically all cases should be tested or only a user input
        """
        self.regenerate = regenerate
        self.automatic_test = automatic_test
        self.start_test()

    @staticmethod
    def initial_with_update_cycle():
        """
        Test that initial document with update in cycle throws exception
        """
        print("LAST TEST (INITIAL BUNDLE WITH UPDATES IN CYCLE) => SHOULD THROW EXCEPTION\n")
        Search(f"@/26/2.txt", "1", False)

    @staticmethod
    def sort_result(x) -> Tuple[str, int, int]:
        def extract_int(z):
            try:
                return int(z.localpart)
            except ValueError:
                return int(z.localpart[6:])

        return x[0], extract_int(x[1]), extract_int(x[2])

    @staticmethod
    def pretty_print(name, result):
        print(name)
        result.sort(key=ResultPrinter.sort_result)
        for i in result:
            print(i)
        print()

    def output(self, file: str | int, strict: bool = False, searched_entity: str = "1"):
        print(f"TEST OF CASE {file} IN MODE {'STRICT' if strict else 'NORMAL'}\n")
        print("Warnings:")
        if isinstance(file, str):
            query: Search = Search(file, searched_entity, strict)
        else:
            query: Search = Search(f"@/{file}/1.txt", searched_entity, strict)
        print()
        self.pretty_print("Valid bundles:", query.result_valid)
        self.pretty_print("Bundles with low-credibility:", query.result_low)
        self.pretty_print("Invalid provenance:", query.result_invalid)
        print()

    def automatic(self):
        """
        Run all cases with searched entity ex:1. Some cases use both normal and strict mode.

        :return: None
        """
        for case in range(1, 27):
            if case in [18, 19, 20, 21, 23, 24]:  # Collection of cases where strict mode should be tested
                for strict in [True, False]:
                    self.output(case, strict)
            else:
                self.output(case)
        try:
            self.initial_with_update_cycle()  # THROWS EXCEPTION
            print("EXCEPTION NOT THROWN IN LAST TEST (WRONG RESULT)")
        except prov.model.Error as e:
            print(f"Exception prov.model.Error with message {e.args[0]} was thrown")

    def start_test(self):
        if self.regenerate:
            print("Generating...", end="")
            CaseGenerator()
            print("done")
        if not self.automatic_test:
            while True:
                document: str | int = input("File or case number (leave empty to exit):")
                if not document:
                    return
                if document.isnumeric():
                    document = int(document)
                strict: bool = input("Strict (1 is yes):") == "1"
                searched_entity: str = input("Local-part of searched entity:")
                print()
                if not searched_entity.isnumeric():
                    print("Local-part of searched entity must be number!\n")
                    continue
                self.output(document, strict, searched_entity)
        self.automatic()


ResultPrinter(True, True)
