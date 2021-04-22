import re
import time
import datetime
import os

def string2Secs(string, formatString="%Y%m%d%H%M%S"):
    try:
        t = datetime.datetime.strptime(string, formatString)
    except:
        t = datetime.datetime.strptime(string, "%Y-%m-%d %H:%M:%S")
    
    return(time.mktime(t.timetuple()))

def secs2String(timestamp, formatString="%Y%m%d%H%M%S"):
    date_time = datetime.datetime.fromtimestamp(timestamp)
    return date_time.strftime(formatString)

def insert_timeStamps(template):
    matches = re.findall("%.",template)
    timeStrings   = [time.strftime(match,time.gmtime(time.time())) for match in matches]
    result = template
    for match, timeString in zip(matches, timeStrings):
        result = result.replace(match,timeString)
        
    return result

def formatStrings2RegEx(template):
    result = template.replace("%Y","\d{4}")

    #matches = re.findall("%(m|d|H|M|S)",result)
    matches = re.findall("%.",result)

    for match in matches:        
        result = result.replace(match, "\d{2}")

    return result

def recursiveFileList(filepath, filterPattern=None):
    result = []
    for root, subdirs, files in os.walk(filepath):
        for f in files:
            r = root.replace(filepath,"").replace("\\","/")
            result.append((r+'/'+f).lstrip('/'))    

    if filterPattern is None:
        return result

    r = re.compile(filterPattern)
    return list(filter(r.match,result))


def split(s,seperator=None):

    # split along white spaces when seperator is None or empty
    if seperator is None or seperator=='':
        return s.split()

    # split into equally spaced chunks if sperator is a number
    if isinstance(seperator, float) or isinstance(seperator, int):
        n = int(seperator)
        return [(s[i:i + n].strip()) for i in range(0, len(s), n)]                

    # split along a specified char    
    return s.split(seperator.replace("\\t","\t"))

def reverse_dict(d):
    rev = {}
    for key in d.keys():
        rev[d[key]] = key
    return rev
    
    
