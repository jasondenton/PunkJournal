class DataVisitor:
    def __init__(self):
        pass

    def visit_list(self, value):
        l = []
        for k in value:
           l.append(self.run(k))
        return l

    def visit_dict(self, value):
        d = {}
        for k in value.keys():
           d[k] = self.run(value[k])
        return d

    def visit_tuple(self, value):
        return tuple(self.visit_list(list(value)))

    def visit_string(self, value):
        return value

    def visit_float(self, value):
        return value

    def visit_int(self, value):
        return value

    def visit_bool(self, value):
        return value

    def visit_unknown(self, value):
        raise Exception('Data Visitor tried to visit a node of type %s' % type(value))

    def run(self, value):
        if isinstance(value, dict):
            return self.visit_dict(value)
        elif isinstance(value, list):
            return  self.visit_list(value)
        elif isinstance(value, str):
            return self.visit_string(value)
        elif isinstance(value, float):
            return self.visit_float(value)
        elif isinstance(value, int):
            return self.visit_int(value)
        elif isinstance(value, bool):
            return self.visit_bool(value)
        elif isinstance(value, tuple):
            return self.visit_tuple(value)
        elif value == None:
            return None
        else:
            return self.visit_unknown(value)



