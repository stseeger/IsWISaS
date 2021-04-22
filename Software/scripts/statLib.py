
#---- first three function are taken from StackOverflow
#    https://stackoverflow.com/questions/15389768/standard-deviation-of-a-list
# this was the pure python solution of Alex Riley
#    https://stackoverflow.com/users/3923281/alex-riley

def mean(data):
    """Return the sample arithmetic mean of data."""
    n = len(data)
    if n < 1:
        raise ValueError('mean requires at least one data point')
    return sum(data)/n

def _ss(data):
    """Return sum of square deviations of sequence data."""
    c = mean(data)
    ss = sum((x-c)**2 for x in data)
    return ss

def sd(data, ddof=1):
    """Calculates the population standard deviation
    by default; specify ddof=1 to compute the sample
    standard deviation."""
    n = len(data)
    if n < 2:
    #    raise ValueError('variance requires at least two data points')
        return 0

    ss = _ss(data)
    pvar = ss/(n-ddof)
    return pvar**0.5

#----------------------------

# this function computes a "trend" for a list of values
# actually it just compares the mean value of the first half with the mean value of the second half
def trendIndex(values):    
    if len(values)==0:
        return float('nan')
    half = round(len(values)/2)
    return(mean(values[half:]) - mean(values[:half]))



if __name__ == "__main__":

    x = [2,3,6,1,8,4,9,20,2]

    print(mean(x))
    print(sd(x))
