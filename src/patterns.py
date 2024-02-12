import re
import collections

class PatternSubstitutions:
    def __init__(self, subs = []):
        self.substitutions = []
        for pat in subs:
            self.add_pattern(pat)

    def add_pattern(self, pattern):
        self.substitutions.append([re.compile(pattern[0]), pattern[1]])

    def process(self,line):
        for pattern in self.substitutions:
            if isinstance(line,str) or isinstance(line,unicode): line = pattern[0].sub(pattern[1],line)
        return line

class PatternBehavior:
    def __init__(self, patterns, matchends=True):
        self.patterns = []
        self.default = None
        self.add_patterns(patterns)
        self.matchends = matchends
        self.lineno = 0

    def nomatch(self, line):
        return

    def add_patterns(self,plst):
        for k in plst:
            self.patterns.append([re.compile(k[0]),k[1]])

    def match_and_process(self,lines):
        if not isinstance(lines,list): lines = [lines]
        for line in lines:
            self.lineno += 1
            for k in self.patterns:
                didmatch = False
                resultgroup = k[0].findall(line)
                for result in resultgroup: 
                    didmatch = True
                    k[1](result)
                if self.matchends and resultgroup: break
            if not didmatch:
                self.nomatch(line)
    
class PatternExecutor:
    def __init__(self, patterns, flags=0):
        self.patterns = []
        self.add_patterns(patterns, flags)

    def add_patterns(self, plst, flags):
        for k in plst:
            self.patterns.append([re.compile(k[0], flags),k[1]])

    def process_line(self, line):
        for k in self.patterns:
                result = k[0].search(line)
                if result:
                    k[1](result.groupdict())
                    return True
        return False