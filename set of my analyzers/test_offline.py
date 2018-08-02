#!/usr/bin/python
# Filename: kpi-test.py
import os
import sys

"""
Offline analysis by replaying logs
"""

# Import MobileInsight modules
from mobile_insight.monitor import OfflineReplayer
# from rlc_ul_retx_analyzer import RlcUlRetxAnalyzer
from ul_sample_analyzer import UlSampleAnalyzer
from ul_lat_breakdown_analyzer import UlLatBreakdownAnalyzer
from ul_mac_latency_analyzer import UlMacLatencyAnalyzer
from lte_cnt_analyzer import LteCntAnalyzer
from dl_lat_breakdown_analyzer import DlLatBdAnalyzer
import cProfile
import re
import dis

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

# try:
#     from line_profiler import LineProfiler
#
#     def do_profile(follow=[]):
#         def inner(func):
#             def profiled_func(*args, **kwargs):
#                 try:
#                     profiler = LineProfiler()
#                     profiler.add_function(func)
#                     for f in follow:
#                         profiler.add_function(f)
#                     profiler.enable_by_count()
#                     return func(*args, **kwargs)
#                 finally:
#                     profiler.print_stats()
#             return profiled_func
#         return inner
#
# except ImportError:
#     def do_profile(follow=[]):
#         "Helpful if you accidentally leave in production!"
#         def inner(func):
#             def nothing(*args, **kwargs):
#                 return func(*args, **kwargs)
#             return nothing
#         return inner

# @do_cprofile # default
# @do_profile()
def kpi_analysis(filename):

    # Get analyzer and log dir from the user

    src = OfflineReplayer()
    # src.set_input_path('../../../logs/0.qmdl')
    # src.set_input_path('../../../logs/exp30_HFDV_byYJ/example.qmdl')
    src.set_input_path(filename)

    # analyzer = LteCntAnalyzer()
    # analyzer = DlLatBdAnalyzer()
    analyzer = UlSampleAnalyzer()
    # analyzer = UlLatBreakdownAnalyzer()
    analyzer.set_source(src)
    # analyzer = LtePdcpGapAnalyzer()
    # analyzer.set_source(src)
#    analyzer1 = PktLossAnalyzer()
#    analyzer1.set_source(src)
#     analyzer2 = RlcUlRetxAnalyzer()
#     analyzer2.set_source(src)
    # analyzer.set_operator("hello")
    # analyzer.set_phone_model("hi")

    # Start the monitoring
    src.run()

# if len(sys.argv) < 2:
#     print "Usage: python [script name] [log pathname]\n"
# exit(0)
# filename = sys.argv[1]
# dis.dis(kpi_analysis)
# print type(res)
# kpi_analysis()
kpi_analysis(sys.argv[1])


