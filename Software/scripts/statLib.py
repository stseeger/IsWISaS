def mean(values):
    if len(values)==0:
        return float('nan')
    return(sum(values)/len(values))

def sd(values):
    if len(values)==0:
        return float('nan')
    m = mean(values)
    return(mean(list(map(lambda x: abs(x-m),values))))

def addLists(list1, list2): return [sum(x) for x in zip(list1, list2)]
def multLists(list1, list2): return [x[0]*x[1] for x in zip(list1, list2)]

# this function computes the slope of a list of values
def slope(values):
    ys = values
    xs = range(len(ys))
    m = ((mean(xs)*mean(ys)) - mean(multLists(xs,ys))) / (mean(xs)**2 - mean(multLists(xs,xs)))
    return(m)

# this function computes a "trend" for a list of values
# actually it just compares the mean value of the first half with the mean value of the second half
def trendIndex(values):    
    if len(values)==0:
        return float('nan')
    half = round(len(values)/2)
    return(mean(values[half:]) - mean(values[:half]))



