import cProfile

def do_cprofile(func):
    def profiled_func(*args, **kwargs):
        profile = cProfile.Profile()
        try:
            profile.enable()
            result = func(*args, **kwargs)
            profile.disable()
            return result
        finally:
            profile.print_stats()
    return profiled_func


def get_item():
    a = 1024
    b = 5
    if a > 1020 and b >4:
        c = a+b


def get_item2():
    a = 1024
    b = 5
    c = 1024*10+b
    if c > 10204:
        d = a+b

@do_cprofile
def test():
    for i in xrange(10):
        print i
        if i ==8:
            break
        get_item()
        get_item2()

test()