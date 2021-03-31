#! /usr/bin/python3

import unittest

import sys_cat

class TestSyscallCategorization(unittest.TestCase):

    def test_sys_cat(self):
        # Pos
        self.assertEqual(sys_cat.syscall_name_to_category("ioctl"), sys_cat.SyscallCategory.HW)
        self.assertEqual(sys_cat.syscall_name_to_category("sys_clone"), sys_cat.SyscallCategory.PROC_LIFE)
        self.assertEqual(sys_cat.syscall_name_to_category("symlinkat"), sys_cat.SyscallCategory.FILE_STATUS)
        self.assertEqual(sys_cat.syscall_name_to_category("sys_selfdestruct"), sys_cat.SyscallCategory.OTHER)

        # Neg
        self.assertNotEqual(sys_cat.syscall_name_to_category("sys_dup2"), sys_cat.SyscallCategory.HW)
        self.assertNotEqual(sys_cat.syscall_name_to_category("reboot"), sys_cat.SyscallCategory.PROC_LIFE)
        self.assertNotEqual(sys_cat.syscall_name_to_category("sysfs"), sys_cat.SyscallCategory.FILE_STATUS)

if __name__ == "__main__":
    unittest.main()