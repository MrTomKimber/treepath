import xmltodict
import os,sys
sys.path.append("../..")
sys.path.append("../../xsdviz")
import treepath.treepath as tp
from treepath.treepath import TreePath

from functools import reduce

import operator

from collections import Counter
from itertools import chain

import pandas as pd

#with open("customer.xsd", "r") as xsdf:
filename = "pacs.008.001.09.xsd"
#filename = "2012_04_XMLSchema.xsd"
#filename = "test copy.xsd"

with open(filename, "r") as xsdf:
    customer_xsd = xsdf.read()
cust_d = xmltodict.parse(customer_xsd)

def access_dict(d,p):
    return reduce(operator.getitem, p , d)

def isnumeric(v):
    return isinstance(v, (int, float, complex)) and not isinstance(v, bool)

cust_tp = tp.TreePath(cust_d)

import xsdparse

primitives_set= {'xs:duration','xs:dateTime','xs:time','xs:date','xs:gYearMonth','xs:gYear',
                'xs:gMonthDay','xs:gDay','xs:gMonth','xs:string','xs:boolean','xs:base64Binary',
                'xs:hexBinary','xs:float','xs:decimal','xs:integer','xs:nonPositiveInteger',
                'xs:negativeInteger','xs:int','xs:short','xs:byte','xs:nonNegativeInteger',
                'xs:unsignedLong','xs:positiveInteger','xs:unsignedInt','xs:unsignedShort',
                'xs:unsignedByte','xs:double','xs:anyURI','xs:QName','xs:NOTATION'}

nameable_xsd_elements = {"xs:attribute", "xs:attributeGroup","xs:complexType", "xs:element", 
                         "xs:group", "xs:key", "xs:keyref", "xs:notation", "xs:simpleType", 
                         "xs:unique", 'xs:primitiveType'}

ref_set = {"xs:attribute", "xs:attributeGroup", "xs:element", "xs:group", }
type_definition_set = {"xs:complexType", "xs:simpleType", "xs:primitiveType" }


# Process XSD into ERD task steps
#1 Load XSD into malleable format

#2 Extract named objects

#3 Extract objects requiring references

#4 Loop over 3, updating object from #1 such that all named objects
#  are complete without any remaining reference updates. 

#5 Extract objects that define types, extensions and restrictions

#6 Reduce singular extensions and restrictions down to their singular/primitive types

#7 Identify objects that describe sequences and other multi-part objects 
#  and associate them with a named parent-type/element

#8 Create tree of joined sequences so as to result in a workable ERD with entities and joins
#  This tree would consist of nodes consisting of multi-part sequences, and elemental
#  types that themselves are pointers to other single-or-multi part sequences.


# Given a tree obj, and some child-tag used to identify nodes within that tree
# build an index used to link paths to their assigned names. 
# Since there's no guarantee of name-uniqueness, each name can refer to 
# one or more paths.

def build_path_index(obj, index_tag="@name"):
    index_d={}
    def store(k,v):
        if k in index_d:
            index_d[k].append(v)
        else:
            index_d[k]=[v]

    for p in TreePath._iterPaths(obj):
        if p[-1]==index_tag:
            #print(p)
            store(access_dict(obj,p), p[:-1])
    return index_d


# Querying the pre-built path_index (see build_path_index) on some key value, 
# choose the path that most closely matches a source_path provided. 
# In practice, this means returning the name most likely to be in scope, 
# when there's some ambiguity in terms of which name to pick.
def return_closest_path_match(path_index_d, key, source_path):

    cand_paths = path_index_d.get(key)
    score_paths = []
    for e,p in enumerate(cand_paths):
        matching_path = TreePath._shortest_common_path([p, source_path])
        score_paths.append( (len(matching_path), len(source_path)-len(matching_path) ) )
    #print(cand_paths, score_paths)
    return cand_paths[score_paths.index(sorted([s for s in score_paths], key=lambda x : (x[0], x[1]))[-1])]
        

# 1) Get the things
#named_things = [p[:-1] for p in TreePath._iterPaths(cust_d) if p[-1]=="@name"]
def gen_labelled_path_dict(info_d, index_tag="@name"):
    things={}
    for name, paths in build_path_index(info_d, index_tag=index_tag).items():
        things[name]=[]
        for path in paths:
            for e,path_element in enumerate(path[::-1]):
                if path_element in nameable_xsd_elements:
                    thing_type=path_element
                    things[name].append((thing_type, path))
                    break
                else:
                    pass
                    
    return things

prims = [{"@name":t} for t in primitives_set]
cust_d['xs:schema']['xs:primitiveType']=prims

named_things=gen_labelled_path_dict(cust_d, index_tag="@name")
things_requiring_reference = build_path_index(cust_d, index_tag="@ref")

#for k in things_requiring_reference:
#    print (k, named_things[k], things_requiring_reference[k])

#referred_things = [p[:-1] for p in TreePath._iterPaths(cust_d) if p[-1]=="@ref"]
#len(named_things),len(referred_things)


all_named_types = set()
named_other_things = set()

for k,v in named_things.items():
    for vv in v:
        if vv[0] in type_definition_set:
            
            all_named_types.add((k, vv[0], tuple(vv[1])))
        else:
            named_other_things.add((k, vv[0], tuple(vv[1])))

            
all_named_types # these will become terminal nodes for type-matching.


# Resolve References
# Loop over the data, taking references where they exist and replacing them with their
# de-referenced lookup values
i=0
finished=False

cust_tp = tp.TreePath(cust_d)

while not finished:
    i = i + 1
    things_requiring_reference = build_path_index(cust_tp.data, index_tag="@ref")
    copy_tp = tp.TreePath(cust_tp.data)
    if len(things_requiring_reference)==0:
        finished=True
        break

    for k,v_list in things_requiring_reference.items():
#        print(k,v_list)
        for e,v in enumerate(v_list):
#            print("\t", e)
            ref_path = return_closest_path_match(named_things,k,v)
#            print("`",v,"`", ref_path)
            retain_content_d={ki:vi for ki,vi in access_dict(copy_tp.data, v).items() if ki != "@ref"}
            cust_tp.set(v, {**retain_content_d, **access_dict(copy_tp.data, ref_path[1])})
    print(i,len(things_requiring_reference))
#k,access_dict(cust_d, things_requiring_reference[k])



cust_tp.data










"""
xsdparse
===========

A utility for parsing an xsd and producing a model specification.

"""
import xmltodict
import zipfile
from collections import Counter
import os, sys
sys.path.append(os.path.abspath("../treepath"))
import treepath.treepath as tp

import pandas as pd
import networkx as nx


def key_scan_obj(obj, search=None, path=None, results=None):
    if results is None:
        results = []
    if search is None:
        search = None
    if path is None:
        path = []
    if isinstance(obj, dict):
        for k,v in obj.items():
            if (k==search or v==search):
                results.append({"path" : path+[k], "value" : v})
            elif isinstance(v, (dict, list)):
                results.extend(key_scan_obj(v, search=search, path=path + [k]))
    elif isinstance(obj, list):
        for e,v in enumerate(obj):
            if v==search:
                results.append({"path" : path+[e], "value" : v})
            elif isinstance(v, (dict, list)):
                results.extend(key_scan_obj(v, search=search, path = path + [e]))
    else:
        if v==search or search is None:
            results.append({"path" : path, "value" : v})
    return results

prims=[ {'@name': 'xs:duration'},
        {'@name': 'xs:dateTime'},
        {'@name': 'xs:time'},
        {'@name': 'xs:date'},
        {'@name': 'xs:gYearMonth'},
        {'@name': 'xs:gYear'},
        {'@name': 'xs:gMonthDay'},
        {'@name': 'xs:gDay'},
        {'@name': 'xs:gMonth'},
        {'@name': 'xs:string'},
        {'@name': 'xs:boolean'},
        {'@name': 'xs:base64Binary'},
        {'@name': 'xs:hexBinary'},
        {'@name': 'xs:float'},
        {'@name': 'xs:decimal'},
        {'@name': 'xs:integer'},
        {'@name': 'xs:nonPositiveInteger'},
        {'@name': 'xs:negativeInteger'},
        {'@name': 'xs:int'},
        {'@name': 'xs:short'},
        {'@name': 'xs:byte'},
        {'@name': 'xs:nonNegativeInteger'},
        {'@name': 'xs:unsignedLong'},
        {'@name': 'xs:positiveInteger'},
        {'@name': 'xs:unsignedInt'},
        {'@name': 'xs:unsignedShort'},
        {'@name': 'xs:unsignedByte'},
        {'@name': 'xs:double'},
        {'@name': 'xs:anyURI'},
        {'@name': 'xs:QName'},
       {'@name': 'xs:NOTATION'},
]
def extract_paths(tree, search_val, path_offset, filter_offset=None, filter_value=None):
    if filter_offset is not None and filter_value is not None:
        extract = [(tuple(k['path'][:path_offset]), k['value']) for k in key_scan_obj(tree, search_val) if k['path'][filter_offset].lower()==filter_value]
    else:
        extract = [(tuple(k['path'][:path_offset]), k['value']) for k in key_scan_obj(tree, search_val) ]
    return extract


def parse_xsd(xsd_bytes):
    xsd_d = xmltodict.parse(xsd_bytes)
    xsd_d['xs:schema']['xs:primitiveType']=prims
    raw_names_d = dict(extract_paths(xsd_d['xs:schema'], "@name", -1))
    raw_bases_d = dict(extract_paths(xsd_d['xs:schema'], "@base", -2, -2, 'xs:restriction') + extract_paths(xsd_d['xs:schema'], "@base", -3, -2, 'xs:extension'))
    raw_types_d = dict(extract_paths(xsd_d['xs:schema'], "@type", -1))
    raw_primitives_d = dict(extract_paths(xsd_d['xs:schema'], "@base", -1, 0, 'xs:primitiveType'))
    raw_primitives_labels_d = {k:"_terminal_" for k,v in raw_primitives_d.items()}

    refs_d = dict([(k,v) for k,v in raw_names_d.items() if not any([p in ['xs:element','xs:attribute'] for p in k[-2:]])])

    # This contains all the specifications required to build the model, keys, (names, types, contextual_clues) TBD: Cardinalities
    specification_d = {k:(v,
                      raw_types_d.get(k, raw_bases_d.get(k,raw_primitives_labels_d.get(k,"_container_"))),
                      "_ref_" if k in refs_d.keys() else "_spec_") for k,v in raw_names_d.items()}

    ref_keys = {v[0]:(k,v[1],v[2]) for k,v in specification_d.items() if v[2]=='_ref_'}
    return raw_names_d, raw_bases_d, raw_types_d, raw_primitives_d, raw_primitives_labels_d, ref_keys, specification_d


def build_(root, spec_d, obj=None):
    ref_keys = {v[0]:(k,v[1],v[2]) for k,v in spec_d.items() if v[2]=='_ref_'}
    if obj is None:
        obj={}
    name, v_type, clue = spec_d.get(root)
    #print(root, name, v_type, clue)
    #print()
    content=[]
    if clue == '_ref_':
        #print("R")
        if v_type == "_container_":
            #print("C")
            for k in spec_d.keys():
                if k[0:len(root)]==root and k!=root:
                    content.append(build_(k, spec_d))
        elif v_type != "_container_" and v_type != "_terminal_":
            #print("!", v_type, clue)
            lookahead = ref_keys.get(v_type)
            if lookahead[1] == "_terminal_":
                content={v_type:{}}
            else:
                content=build_( lookahead[0], spec_d)
        else:
            content=name
    elif clue == '_spec_':

        #print (name, v_type, ref_keys.get(v_type))
        content=build_( ref_keys.get(v_type)[0], spec_d)

    else:
        assert False
        return name, v_type, clue
    obj[name]=content
    return obj

