#!/usr/bin/env python3
import os
from pandare import Panda

# Step 1: create recording of a few commands running

panda = Panda(generic="x86_64")

if not os.path.isfile("pe_test-rr-snp"):
    @panda.queue_blocking
    def drive():
        panda.record_cmd("whoami; ls; find /etc | grep foo", recording_name="pe_test")
        panda.end_analysis()

    panda.run()


# Step 2: replay the recording with plugins required for pandelephant data collection
panda.load_plugin("syscalls_logger")
panda.load_plugin("asidstory")
panda.set_pandalog("pe_test.plog")

panda.run_replay("pe_test")

# Now consume pe_test.plog with pandelephant. For example:
#   python3 -m pandelephant.parser --db_url=[postgresql://...] --pandalog pe_test.plog --exec_name test
