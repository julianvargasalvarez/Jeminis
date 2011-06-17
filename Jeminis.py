# -*- coding: cp1252 -*-
import pyodbc
from pyodbc import *

import os
from os import listdir

import sys
from sys import path

import pickle
from pickle import *

from Tkinter import *

import re
from re import *

tcache = list()  # global list for loading templates
templateFolder    = "" 
formsFolder       = ""
_loadingCatalog   = list() # Handlers for event LoadingCatalog
_catalogLoaded    = list() # Handlers for event CatalogLoaded
_loadingTemplates = list() # Handlers for event LoadingTemplates
_templatesLoaded  = list() # Handlers for event TemplatesLoaded
_loadingForms     = list() # Handlers for event LoadingForms
_formsLoaded      = list() # Handlers for event FormsLoaded
_runningProcess   = list() # Handlers for event RunningProcess
_processFinished  = list() # Handlers for event ProcessFiniched
ConectionString   = ""

class jeminis(list):
    
    def __init__(self):
        # A dictionary for storing
        # the template (key) and the
        # final code (value)
        self.finalCode = dict() 
 
#----------------------------------------------------
#   General        
#----------------------------------------------------
    def LoadingCatalog(self, handler):
        global _loadingCatalog
        _loadingCatalog.append(handler)
        return self

    def CatalogLoaded(self, handler):
        global _catalogLoaded
        _catalogLoaded.append(handler)
        return self

    def LoadingTemplates(self, handler):
        global _loadingTemplates
        _loadingTemplates.append(handler)
        return self

    def TemplatesLoaded(self, handler):
        global _templatesLoaded
        _templatesLoaded.append(handler)
        return self

    def LoadingForms(self, handler):
        global _loadingForms
        _loadingForms.append(handler)
        return self

    def FormsLoaded(self, handler):
        global _formsLoaded
        _formsLoaded.append(handler)
        return self

    def RunningProcess(self, handler):
        global _runningProcess
        _runningProcess.append(handler)
        return self
    
    def ProcessFinished(self, handler):
        global _processFinished
        _processFinished.append(handler)
        return self

    def Save(self, path):
        f = open(path, 'w')
        pickle.dump(self, f)
        return self

    def Load(self, path):
        f = open(path, 'r')
        self = pickle.dump(f)
        return self
    
    def TemplateFolder(self, path):
        global templateFolder
        templateFolder = path
        return self

#----------------------------------------------------
#    Selectors
#----------------------------------------------------
    
    def __isAllSelector(self, selector):
        return (selector.replace(' ', '') == '*')

    def __SelectAll(self, root, nodes):
        nodes.append(root)
        for child in root:
            nodes = self.__SelectAll(child, nodes)
        return nodes
    
    def __isFunctionSelector(self, selector):
        lengthFunction = len(re.findall('(\w*)\((\'.*\')\)', selector)) # function signature, for instance: myFun('params')
        return (lengthFunction == 1)

    def __MatchSelectFunction(self, selector, root):
        fN, parameters = re.findall('(\w*)\((\'.*\')\)', selector)[0] # tuple ('funName', "'Selector'")
        funName = fN.replace(':', '')
        result = jeminis()
        for node in root("*"):
            if funName in dir(node):
                if node.__getattribute__(funName)(node, parameters):
                    result.append(node)
        
        return result

    def __isAttributeSelector(self, selector):
        lengthAll = len(re.findall('(\[.*?\])', selector))#any character enclosed in brackets
        lengthSimple = len(re.findall('(\[\w+\])', selector)) #any Word enclosed in brackets
        return (lengthAll == 1 and lengthSimple == 1)

    def __MatchAttribute(self, selector, root):
        attr = re.findall('\[(\w+)\]', selector)[0]
        result = jeminis()
        for node in root("*"):
            if attr in dir(node):
                result.append(node)
        
        return result
    

    def __isComparisonSelector(self, selector):
        lengthAll = len(re.findall('(\[.*?\])', selector))#any character enclosed in brackets
        lengthComp = len(re.findall('(\[\w*(=|\!=|\^=|\$=|\*=)\'.*\'\])', selector)) #any Word followed by operator and value
        return (lengthAll == 1 and lengthComp == 1)

    def __MatchCompareAttribute(self, selector, root):
        s, attr, opr, value = re.findall('(\[(\w*)(=|\!=|\^=|\$=|\*=)(\'.*\')\])', selector)[0]
        value = value.replace("'", "") # remove the quotes
        result = jeminis()
        for node in root("*"):
            if attr in dir(node):
                val = node.__getattribute__(attr)
                
                if   opr == '=':
                    if val == value: result.append(node)
    
                elif opr == '!=':
                    if re.match(value+'!', val): result.append(node)
    
                elif opr == '^=':
                    if re.match('^'+value, val): result.append(node)
    
                elif opr == '$=':
                     if re.match(value+'$', val): result.append(node)
    
                elif opr == '*=':
                    if re.match(value+'*', val): result.append(node)

        return result

    
    def __isOrSelector(self, selector):
        return len(selector.split(',')) > 1

    def __MatchOrSelector(self, selector, root):
        match = False
        result = jeminis()
        
        for sel in selector.split(','):
            result.extend(self.__matchSelector(root, sel))

        return result
            
    def __isAncestorDescendantSelector(self, selector):
        lengthAll = len(re.findall('(\[.*?\])\s+(\[.*?\])', selector))#two selectors separated by spaces
        return (lengthAll == 1)

    def __MatchAncestorDescendant(self, selector, root):
        selAncestor, selDescendant = re.findall('(\[.*?\])\s+(\[.*?\])', selector)[0]
        ancestor = root(selAncestor)
        
        return self.__matchSelector(ancestor, selDescendant)
            
    def __isParentChildSelector(self, selector):
        lengthAll = len(re.findall('(\[.*?\])\s*>\s*(\[.*?\])', selector))#two selectors separated by >
        return (lengthAll == 1)

    def __MatchParentChild(self, selector, root):
        selParent, selChild = re.findall('(\[.*?\])\s*>\s*(\[.*?\])', selector)[0]
        parent = root(selParent)
        result = jeminis()
        for node in parent:
            if node == node(selChild):
                result.append(node)
        return result
            
    def __isChildParentSelector(self, selector):
        lengthAll = len(re.findall('(\[.*?\])\s*<\s*(\[.*?\])', selector))#two selectors separated by <
        return (lengthAll == 1)

    def __MatchChildParent(self, selector, root):
        selChild, selParent = re.findall('(\[.*?\])\s*<\s*(\[.*?\])', selector)[0]
        child = self(selChild)
        parent = self(selParent)
        result = jeminis()
        
        if child in parent:
            result = child
               
        return result

    def __isDepParentChildSelector(self, selector):
        lengthAll = len(re.findall('(\[.*?\])\s*\:>\s*(\[.*?\])', selector))#two selectors separated by :>
        return (lengthAll == 1)

    def __MatchDepParentChild(self, selector, root):
        return True

    def __isDepChildParentSelector(self, selector):
        lengthAll = len(re.findall('(\[.*?\])\s*<\:\s*(\[.*?\])', selector))#two selectors separated by <:
        return (lengthAll == 1)

    def __MatchDepChildParent(self, selector, root):
        return True

    def __isAndSelector(self, selector):
        lengthAll = len(re.findall('(\[.*?\])', selector))   # any character enclosed in brackets
        lengthsapce = len(re.findall('(\]\s+\[)', selector)) # closing and opening brackets separated by space
        lengthother = len(re.findall('(\].+\[)', selector))  # closing and opening brackets separated by any character
        return (lengthAll > 1 and lengthsapce == 0 and lengthother == 0)

    def __MatchAndSelector(self, selector, root):
        result = root
        for sel in re.findall('(\[.*?\])', selector):
            result = result(sel)
                
        return result
        
    def __matchSelector(self, node, selector):
        result = jeminis()
        if self.__isOrSelector(selector):
            result = self.__MatchOrSelector(selector, node)

        elif self.__isAndSelector(selector):
            result = self.__MatchAndSelector(selector, node)

        elif self.__isFunctionSelector(selector):
            result = self.__MatchSelectFunction(selector, node)

        elif self.__isAttributeSelector(selector):
            result = self.__MatchAttribute(selector, node)

        elif self.__isComparisonSelector(selector):
            result = self.__MatchCompareAttribute(selector, node)

        elif self.__isAncestorDescendantSelector(selector):
            result = self.__MatchAncestorDescendant(selector, node)

        elif self.__isParentChildSelector(selector):
            result = self.__MatchParentChild(selector, node)

        elif self.__isChildParentSelector(selector):
            result = self.__MatchChildParent(elector, node)

        elif self.__isDepParentChildSelector(selector):
            result = self.__MatchDepParentChild(selector, node)

        elif self.__isDepChildParentSelector(selector):
            result = self.__MatchDepChildParent(selector, node)

        elif self.__isAllSelector(selector):
            result = self.__SelectAll(node, jeminis())

        return result
    
#----------------------------------------------------
    
    def __call__(self, selector):
        """
        Navigates through all the hierarchy
        looking for matching objects and add them to
        the new list that will be returned
        """
        nodes = self.__matchSelector(self, selector)
        
        if len(nodes) == 1:
            nodes = nodes[0]

        return nodes
#----------------------------------------------------

    def Sync(self):

        cnxn = pyodbc.connect(self.ConectionString)
        cursor = cnxn.cursor()

        #SCHEMATA
        cursor.execute("""
            Select CATALOG_NAME, SCHEMA_NAME, DEFAULT_CHARACTER_SET_NAME
            From INFORMATION_SCHEMA.SCHEMATA
        """)

        for Schemata in cursor.fetchall():
            nodeSchemata = jeminis()
            nodeSchemata.name                       = Schemata.SCHEMA_NAME
            nodeSchemata.CATALOG_NAME               = Schemata.CATALOG_NAME
            nodeSchemata.SCHEMA_NAME                = Schemata.SCHEMA_NAME
            nodeSchemata.DEFAULT_CHARACTER_SET_NAME = Schemata.DEFAULT_CHARACTER_SET_NAME
            self.append(nodeSchemata)
            #print("Schema '" + nodeSchemata.SCHEMA_NAME + "' added to the catalog")

            #TABLES
            cursor.execute("""
                Select TABLE_CATALOG, TABLE_SCHEMA, TABLE_NAME, TABLE_TYPE
                From INFORMATION_SCHEMA.TABLES
                Where TABLE_SCHEMA = '""" + nodeSchemata.SCHEMA_NAME +"""'
                And TABLE_TYPE ='BASE TABLE'
            """)

            for Table in cursor.fetchall():
                nodeTable = jeminis()
                nodeTable.name = Table.TABLE_NAME
                nodeTable.TABLE_CATALOG = Table.TABLE_CATALOG
                nodeTable.TABLE_SCHEMA  = Table.TABLE_SCHEMA
                nodeTable.TABLE_NAME    = Table.TABLE_NAME
                nodeTable.TABLE_TYPE    = Table.TABLE_TYPE
                nodeSchemata.append(nodeTable)
                #print("\tTable '" + nodeTable.TABLE_NAME +"' added to the catalog")

                #COLUMNS for tables
                cursor.execute("""
                    Select TABLE_CATALOG, TABLE_SCHEMA, TABLE_NAME,
                    COLUMN_NAME, ORDINAL_POSITION, COLUMN_DEFAULT,
                    IS_NULLABLE, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH,
                    CHARACTER_OCTET_LENGTH, NUMERIC_PRECISION,
                    NUMERIC_SCALE, CHARACTER_SET_NAME, COLLATION_NAME
                    From INFORMATION_SCHEMA.COLUMNS
                    Where TABLE_NAME = '""" + nodeTable.TABLE_NAME + """'
                """)

                for Column in cursor.fetchall():
                    nodeColumn = jeminis()
                    nodeColumn.name                     = Column.COLUMN_NAME
                    nodeColumn.TABLE_CATALOG            = Column.TABLE_CATALOG
                    nodeColumn.TABLE_SCHEMA             = Column.TABLE_SCHEMA
                    nodeColumn.TABLE_NAME               = Column.TABLE_NAME
                    nodeColumn.COLUMN_NAME              = Column.COLUMN_NAME
                    nodeColumn.ORDINAL_POSITION         = Column.ORDINAL_POSITION
                    nodeColumn.COLUMN_DEFAULT           = Column.COLUMN_DEFAULT
                    nodeColumn.IS_NULLABLE              = Column.IS_NULLABLE
                    nodeColumn.DATA_TYPE                = Column.DATA_TYPE
                    nodeColumn.CHARACTER_MAXIMUM_LENGTH = Column.CHARACTER_MAXIMUM_LENGTH
                    nodeColumn.CHARACTER_OCTET_LENGTH   = Column.CHARACTER_OCTET_LENGTH
                    nodeColumn.NUMERIC_PRECISION        = Column.NUMERIC_PRECISION
                    nodeColumn.NUMERIC_SCALE            = Column.NUMERIC_SCALE
                    nodeColumn.CHARACTER_SET_NAME       = Column.CHARACTER_SET_NAME
                    nodeColumn.COLLATION_NAME           = Column.COLLATION_NAME
                    nodeTable.append(nodeColumn)
                    #print("\t\tColumn '" + nodeColumn.COLUMN_NAME +"' added to the catalog")

                #print("")
            
            #VIEWS
            cursor.execute("""
                Select TABLE_CATALOG, TABLE_SCHEMA, TABLE_NAME,
                VIEW_DEFINITION, CHECK_OPTION, IS_UPDATABLE
		From INFORMATION_SCHEMA.VIEWS
		Where TABLE_SCHEMA = '""" + nodeSchemata.SCHEMA_NAME +"""'
            """)
                
            for View in cursor.fetchall():
                nodeView= jeminis()
                nodeView.name            = View.TABLE_NAME
                nodeView.TABLE_CATALOG   = View.TABLE_CATALOG
                nodeView.TABLE_SCHEMA    = View.TABLE_SCHEMA
                nodeView.TABLE_NAME      = View.TABLE_NAME
                nodeView.VIEW_DEFINITION = View.VIEW_DEFINITION
                nodeView.CHECK_OPTION    = View.CHECK_OPTION
                nodeView.IS_UPDATABLE    = View.IS_UPDATABLE
                nodeSchemata.append(nodeView)
                #print("\tView '" + nodeView.TABLE_NAME +"' added to the catalog")

                #COLUMNS for View
                cursor.execute("""
                    Select TABLE_CATALOG, TABLE_SCHEMA, TABLE_NAME,
                    COLUMN_NAME, ORDINAL_POSITION, COLUMN_DEFAULT,
                    IS_NULLABLE, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH,
                    CHARACTER_OCTET_LENGTH, NUMERIC_PRECISION,
                    NUMERIC_SCALE, CHARACTER_SET_NAME, COLLATION_NAME
                    From INFORMATION_SCHEMA.COLUMNS
                    Where TABLE_NAME = '""" + nodeView.TABLE_NAME + """'
                """)

                for Column in cursor.fetchall():
                    nodeColumn = jeminis()
                    nodeColumn.name                     = Column.COLUMN_NAME
                    nodeColumn.TABLE_CATALOG            = Column.TABLE_CATALOG
                    nodeColumn.TABLE_SCHEMA             = Column.TABLE_SCHEMA
                    nodeColumn.TABLE_NAME               = Column.TABLE_NAME
                    nodeColumn.COLUMN_NAME              = Column.COLUMN_NAME
                    nodeColumn.ORDINAL_POSITION         = Column.ORDINAL_POSITION
                    nodeColumn.COLUMN_DEFAULT           = Column.COLUMN_DEFAULT
                    nodeColumn.IS_NULLABLE              = Column.IS_NULLABLE
                    nodeColumn.DATA_TYPE                = Column.DATA_TYPE
                    nodeColumn.CHARACTER_MAXIMUM_LENGTH = Column.CHARACTER_MAXIMUM_LENGTH
                    nodeColumn.CHARACTER_OCTET_LENGTH   = Column.CHARACTER_OCTET_LENGTH
                    nodeColumn.NUMERIC_PRECISION        = Column.NUMERIC_PRECISION
                    nodeColumn.NUMERIC_SCALE            = Column.NUMERIC_SCALE
                    nodeColumn.CHARACTER_SET_NAME       = Column.CHARACTER_SET_NAME
                    nodeColumn.COLLATION_NAME           = Column.COLLATION_NAME
                    nodeTable.append(nodeColumn)
                    #print("\t\tColumn '" + nodeColumn.COLUMN_NAME +"' added to the catalog")

                #print("")

            #ROUTINES
            cursor.execute("""
                Select SPECIFIC_NAME, ROUTINE_CATALOG, ROUTINE_SCHEMA,
                ROUTINE_NAME, ROUTINE_TYPE, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH,
                CHARACTER_OCTET_LENGTH, COLLATION_NAME, CHARACTER_SET_NAME,
                NUMERIC_PRECISION, NUMERIC_SCALE, DTD_IDENTIFIER, ROUTINE_BODY,
                ROUTINE_DEFINITION, EXTERNAL_NAME, EXTERNAL_LANGUAGE,
                PARAMETER_STYLE, IS_DETERMINISTIC, SQL_DATA_ACCESS, SQL_PATH,
                CREATED, LAST_ALTERED
		From INFORMATION_SCHEMA.ROUTINES
		Where ROUTINE_SCHEMA = '"""+ nodeSchemata.SCHEMA_NAME +"""'
            """)
                
            for Routine in cursor.fetchall():
                nodeRoutine = jeminis()
                nodeRoutine.name                     = Routine.ROUTINE_NAME
                nodeRoutine.SPECIFIC_NAME            = Routine.SPECIFIC_NAME
                nodeRoutine.ROUTINE_CATALOG          = Routine.ROUTINE_CATALOG
                nodeRoutine.ROUTINE_SCHEMA           = Routine.ROUTINE_SCHEMA
                nodeRoutine.ROUTINE_NAME             = Routine.ROUTINE_NAME
                nodeRoutine.ROUTINE_TYPE             = Routine.ROUTINE_TYPE
                nodeRoutine.DATA_TYPE                = Routine.DATA_TYPE
                nodeRoutine.CHARACTER_MAXIMUM_LENGTH = Routine.CHARACTER_MAXIMUM_LENGTH
                nodeRoutine.CHARACTER_OCTET_LENGTH   = Routine.CHARACTER_OCTET_LENGTH
                nodeRoutine.COLLATION_NAME           = Routine.COLLATION_NAME
                nodeRoutine.CHARACTER_SET_NAME       = Routine.CHARACTER_SET_NAME
                nodeRoutine.NUMERIC_PRECISION        = Routine.NUMERIC_PRECISION
                nodeRoutine.NUMERIC_SCALE            = Routine.NUMERIC_SCALE
                nodeRoutine.DTD_IDENTIFIER           = Routine.DTD_IDENTIFIER
                nodeRoutine.ROUTINE_BODY             = Routine.ROUTINE_BODY
                nodeRoutine.ROUTINE_DEFINITION       = Routine.ROUTINE_DEFINITION
                nodeRoutine.EXTERNAL_NAME            = Routine.EXTERNAL_NAME
                nodeRoutine.EXTERNAL_LANGUAGE        = Routine.EXTERNAL_LANGUAGE
                nodeRoutine.PARAMETER_STYLE          = Routine.PARAMETER_STYLE
                nodeRoutine.IS_DETERMINISTIC         = Routine.IS_DETERMINISTIC
                nodeRoutine.SQL_DATA_ACCESS          = Routine.SQL_DATA_ACCESS
                nodeRoutine.SQL_PATH                 = Routine.SQL_PATH
                nodeRoutine.CREATED                  = Routine.CREATED
                nodeRoutine.LAST_ALTERED             = Routine.LAST_ALTERED
                nodeSchemata.append(nodeRoutine)
                #print("\tRoutine '" + nodeRoutine.ROUTINE_NAME +"' added to the catalog")

                #PARAMETERS for Routines
                cursor.execute("""
                    Select SPECIFIC_CATALOG, SPECIFIC_SCHEMA, SPECIFIC_NAME,
                    ORDINAL_POSITION, PARAMETER_MODE, PARAMETER_NAME, DATA_TYPE,
                    CHARACTER_MAXIMUM_LENGTH, CHARACTER_OCTET_LENGTH, COLLATION_NAME,
                    CHARACTER_SET_NAME, NUMERIC_PRECISION, NUMERIC_SCALE
                    From INFORMATION_SCHEMA.PARAMETERS
                    Where SPECIFIC_NAME ='""" + nodeRoutine.SPECIFIC_NAME +"""'
                """)

                for Parameter in cursor.fetchall():
                    nodeParameter = jeminis()
                    nodeParameter.name                      = Parameter.PARAMETER_NAME
                    nodeParameter.SPECIFIC_CATALOG          = Parameter.SPECIFIC_CATALOG
                    nodeParameter.SPECIFIC_SCHEMA           = Parameter.SPECIFIC_SCHEMA
                    nodeParameter.SPECIFIC_NAME             = Parameter.SPECIFIC_NAME
                    nodeParameter.ORDINAL_POSITION          = Parameter.ORDINAL_POSITION
                    nodeParameter.PARAMETER_MODE            = Parameter.PARAMETER_MODE
                    nodeParameter.PARAMETER_NAME            = Parameter.PARAMETER_NAME
                    nodeParameter.DATA_TYPE                 = Parameter.DATA_TYPE
                    nodeParameter.CHARACTER_MAXIMUM_LENGTH  = Parameter.CHARACTER_MAXIMUM_LENGTH
                    nodeParameter.CHARACTER_OCTET_LENGTH    = Parameter.CHARACTER_OCTET_LENGTH
                    nodeParameter.COLLATION_NAME            = Parameter.COLLATION_NAME
                    nodeParameter.CHARACTER_SET_NAME        = Parameter.CHARACTER_SET_NAME
                    nodeParameter.NUMERIC_PRECISION         = Parameter.NUMERIC_PRECISION
                    nodeParameter.NUMERIC_SCALE             = Parameter.NUMERIC_SCALE
                    nodeRoutine.append(nodeParameter)
                    #print("\t\tParameter '" + nodeParameter.PARAMETER_NAME +"' added to the catalog")
                #print("")

            #CONSTRAINTS
            cursor.execute("""
                Select kcu.CONSTRAINT_CATALOG, kcu.CONSTRAINT_SCHEMA, kcu.CONSTRAINT_NAME, 
                kcu.TABLE_CATALOG, kcu.TABLE_SCHEMA, kcu.TABLE_NAME, kcu.COLUMN_NAME,
                kcu.ORDINAL_POSITION, tc.CONSTRAINT_TYPE
                From INFORMATION_SCHEMA.KEY_COLUMN_USAGE kcu
                Left Join
                INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc
                On kcu.CONSTRAINT_NAME = tc.CONSTRAINT_NAME
                Where kcu.CONSTRAINT_SCHEMA = '""" + nodeSchemata.SCHEMA_NAME + """'
            """)
                
            for Constraint in cursor.fetchall():
                nodeConstraint= jeminis()
                nodeConstraint.name               = Constraint.CONSTRAINT_NAME
                nodeConstraint.CONSTRAINT_CATALOG = Constraint.CONSTRAINT_CATALOG
                nodeConstraint.CONSTRAINT_SCHEMA  = Constraint.CONSTRAINT_SCHEMA
                nodeConstraint.CONSTRAINT_NAME    = Constraint.CONSTRAINT_NAME
                nodeConstraint.TABLE_CATALOG      = Constraint.TABLE_CATALOG
                nodeConstraint.TABLE_SCHEMA       = Constraint.TABLE_SCHEMA
                nodeConstraint.TABLE_NAME         = Constraint.TABLE_NAME
                nodeConstraint.COLUMN_NAME        = Constraint.COLUMN_NAME
                nodeConstraint.ORDINAL_POSITION   = Constraint.ORDINAL_POSITION
                nodeConstraint.CONSTRAINT_TYPE    = Constraint.CONSTRAINT_TYPE
                nodeSchemata.append(nodeConstraint)
                #print("\tConstraint '" + nodeConstraint.CONSTRAINT_NAME +"' added to the catalog")

            #print("")
        
    def LoadCatalog(self, connectionString):
        """ Connects to the database 'db' and load the catalog to
        correspondent in-memory representation """
        
        # calls cutom functions before loading the catalog
        global _loadingCatalog
        for handler in _loadingCatalog: 
            handler()

        self.ConectionString = connectionString
        self.Sync()

        # calls cutom functions after loading the catalog
        global _catalogLoaded
        for handler in _catalogLoaded: 
            handler(self)
            
        return self

    def Run(self):
        global _runningProcess
        for handler in _runningProcess:
            handler()
            
        self.loadTemplates()
        global tcache
        for t in tcache:
            print("Running code transformation for template '" + t.name + "'")
            t.Run(self)# for each template loaded, runs the code generation process
                
            print("")

        global _processFinished
        for handler in _processFinished:
            handler()
            
        return self

    def LoadTemplates(self):

        global tcache
        global templateFolder
        global _loadingTemplates
        global _templatesLoaded
        
        if len(tcache) == 0 and (not templateFolder == ""):
            print("Templates folder '" + templateFolder + "'")
            for fname in os.listdir(templateFolder):
                for handler in _loadingTemplates:
                    handler(fname)
                        
                templateFile = open(templateFolder + "\\" + fname, "r")
                t = template()
                t.body = templateFile.read().decode('utf_8')
                t.name = fname
                tcache.append(t)
                print("Templated '" + fname +"' to the cache.")
                templateFile.close()

                for handler in _templatesLoaded:
                    handler(t)

        return sel    
    
    def ShowForm(self, path):
        form(path, self)
        return self

class template(object):

    def __init__(self):
        self.body = ""
        self.expression = '(?P<template>.*\(:(.+)\n([\s\S\w\W.]+|(?P=template)):\).*)'
        self.name = ""

    def Run(self, target):
        temp = jeminis()
        temp.append(target)
        temp.name=''
        template = self.__g(self.body, self.expression, temp)
        target.finalCode[self.name] = template
        #print("The final code was \n" + template + "\n\n")
        
    def __g(self, t, r, obj):
        parts    = re.findall(r, t)
        subExp   = ''
        selector = ''
        theRest  = ''
        for i in parts:
            subExp, selector, theRest = i
            
            if(len(obj) > 0):
                strSubCode = ''
            else:
                strSubCode = theRest

            for childNode in obj(selector):
                strSubCode += self.__g(theRest, r, childNode)

            t = t.replace(re.findall('(\(:(.+)\n[\s\S\w\W.]+:\))',subExp)[0][0], strSubCode)            
                
        for p in re.findall('\$(\w+)', t):
            if p in dir(obj):
                val = obj.__getattribute__(p)
            else:
                val = '$'+p

            t = t.replace('$'+p, val)

        return t
       

class form(Frame):
    def __init__(self, path, context):
        f = open(path, 'r')
        content = f.readlines()
        f.close()
        Frame.__init__(self, None)
        self.grid()
        self.rows = len(content)
        self.columnForControl = 0
        self.fields = dict()
        self.context = context
        
        for field in content:
            if field <> content[0]:
                parts = field.split()
                ctr = self.createControl(parts, content.index(field))
        
        self.master.title(content[0])
        self.mainloop()
        
    def createControl(self, description, index):
        name = description[0]
        desc = description[1].rstrip().lstrip().lower()
                
        if desc == 'string':
            label = Label(self, text=name)
            label.grid(row=index, column=0)
            self.fields[name] = StringVar()
            entry = Entry(self, bd=5, textvariable = self.fields[name])
            entry.grid(row=index, column=1, columnspan=self.columnForControl+1)
            return entry
        
        elif desc == 'number':
            label = Label(self, text=name)
            label.grid(row=index, column=0)
            self.fields[name] = StringVar()
            entry = Entry(self, bd=5, textvariable = self.fields[name])
            entry.grid(row=index, column=1, columnspan=self.columnForControl+1)
            return entry
        
        elif desc == 'bool':
            self.fields[name] = StringVar()
            chk = Checkbutton(self, text = name, textvariable = self.fields[name])
            chk.grid(row=index, column=1, columnspan=self.columnForControl+1)
            return chk
        
        elif desc.startswith('select'):
            label = Label(self, text=name)
            label.grid(row=index, column=0)
            opt = desc.split('(')[1].split(')')[0].split(',')
            self.fields[name] = StringVar()
            lst = Spinbox(self, values=opt, textvariable = self.fields[name])
            lst.grid(row=index, column=1, columnspan=self.columnForControl+1)
            return lst
        
        elif desc.startswith('method'):
            handlerName = re.findall('\s*\(\s*(\w+)\s*\)\s*', desc)[0]
            btn = Button(self, text=name)
            btn.grid(row=self.rows, column=self.columnForControl)
            self.columnForControl += 1
            btn.bind("<Button-1>", self.context.__getattribute__(handlerName))
            
            return btn


