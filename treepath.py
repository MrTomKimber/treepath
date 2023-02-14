import copy
from functools import reduce
import operator
import json
import pandas as pd
import hashlib
import networkx as nx

class vdict(dict):
    def __missing__(self, key):
        value = self[key] = type(self)()
        return value

class TreePath(object):
    def __init__(self, obj: object):
        self.data = copy.deepcopy(obj)

    @staticmethod
    def _hashpath(path, length=64):
        return hashlib.sha256(bytes(str(tuple(path)).encode())).hexdigest()[0:length]

    def to_dag(self):
        dag = nx.DiGraph()
        edge_set = set()
        nodemap = {}
        hashmap = {}
        paths_by_length = sorted(self._all_paths(self.data), key = lambda x : len(x))
        for p in paths_by_length:
            tuple_p = tuple(p)
            hashmap[self._hashpath(p)]=tuple_p
        edge_set = set()
        inv_hashmap = {v:k for k,v in hashmap.items()}
        for k,v in hashmap.items():

            dag.add_node(k, data={"path" : list(v), "label" : v[-1]})
#            enodes = ((inv_hashmap[tuple(v[e]]),inv_hashmap[v[e+1]]) for e,q in enumerate(v[0:-2]))
            enodes = ((inv_hashmap[v[0:e]], inv_hashmap[v[0:e+1]]) for e in range(1,len(v)))
#            print(list(enodes))
            for edge in enodes:

                if edge not in edge_set:
                    dag.add_edge(*edge)
                    edge_set.add(edge)
        return dag

    def has_path(self, path: list):
        try:
            x = self.get(path)
            return True
        except (KeyError, TypeError):
            return False

    def get(self, path : list):
        return reduce(operator.getitem, path, self.data)

    def set(self, path: list, value):
        """Hard set of value to a path variable - if any value existed previously, it is overwritten.
        Throws an error if the path doesn't exist"""
        if not self.has_path(path[:-1]):
            raise KeyError(path)
        else:
            if len(path)>1:
                self.get(path[:-1])[path[-1]]=value
            else:
                self.data[path[0]]=value

    @staticmethod
    def _path_to_nested_d(path, value=None):
        nested_d = TreePath({})
        build_p = []
        for p in path:
            build_p = build_p + [p]
            nested_d.set(build_p,{})
        build_p = build_p + [value]
        nested_d.set(build_p, {})
        return nested_d.data

    def add(self, path : list, value, default={}):
        sep = self._shortest_existing_path(path)

        if sep != []:
            rem = path[len(sep):]
            fill = self.get(sep)
        else:
            rem = path[1:]
            #print("!", sep, rem)
            fill = {}
            sep=[path[0]]
        if len(rem)>0:
            rem_p = self._path_to_nested_d(rem, value)
        else:
            rem_p = { value : {}}
        #print(sep, "fill", fill, "rem", rem_p)
        self.set(sep,{**fill, **rem_p})

    def _shortest_existing_path(self, path: list):
        epath = []
        for p in path:
            if self.has_path(epath + [p]):
                epath = epath + [p]
            else:
                break
        return epath

    @staticmethod
    def walk(node, path=None):
        if path is None:
            path=[]
        empty_dict = {}
        for key, item in node.items():
            if isinstance(item,dict):
                if item != empty_dict:
                    for w in TreePath.walk(item, path + [key]):
                        yield w
                else:
                    yield path, key
            else:
                yield item

    @staticmethod # experimental
    def _iterItems(variable):
        if isinstance(variable, (str, int, float, bool)):
            yield None
        elif isinstance(variable, dict):
            for k,v in variable.items():
                yield k,v
        elif isinstance(variable, (list, tuple)):
            for k in range(0,len(variable)):
                yield k, variable[k]
        else:
            raise StopIteration

    @staticmethod
    # The _iterKeys returns a single interface onto dict and list objects for "getting" underlying values
    def _iterKeys(variable):
        if isinstance(variable, (str, int, float, bool)):
            yield None
        elif isinstance(variable, dict):
            for k in variable.keys():
                yield k
        elif isinstance(variable, (list, tuple)):
            for k in range(0,len(variable)):
                yield k
        else:
            raise StopIteration

    # Generator returning all leaf node paths for a given object (without first enumerating all paths).
    @classmethod
    def _iterLeaves(cls, obj, path=None):
        if path is None:
            path=[]
        for key in cls._iterKeys(obj):
            if isinstance(obj[key], (dict, list)) and len(obj[key])>0:
                for p in cls._iterLeaves(obj[key], path + [key]):
                    yield p
            else:
                yield(path + [key])

    # Generator returning all paths from source in object
    @classmethod
    def _iterPaths(cls, data, path=None):
        if path is None:
            path=[]
        keys = cls._iterKeys(data)
        for k in keys:
            yield path + [k]
            if isinstance(data[k], (dict, list)):
                for p in cls._iterPaths(data[k], path + [k]):
                    yield p
            

    @classmethod
    def _all_paths(cls, data, path=None, paths=None):
        return list(cls._iterPaths(data))

    @staticmethod
    def _shortest_common_path(path_list):
        best = 0
        shortest_length = min([len(p) for p in path_list])
        for loc in range(0, shortest_length):
            if all([p[loc]==path_list[0][loc] for p in path_list]):
                best = loc
            else:
                break
        return path_list[0][0:best+1]
