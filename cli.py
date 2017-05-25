#!/tools/bin/python2.7

import re
from dd.runtime import api
api.load("qt_py")
from Qt import QtGui, QtWidgets, QtCore, _common_members


def find_things(lines):
    """
    find_things will look for any uses of QtGui or QtCore as well as any uses of "from [PySide|PyQt4] import .*"
    It stores these and returns them as a list of tuples. module, function and line index.

    :param list lines: List of lines of the file that we are reading.
    :return: List of matches that it found in the file. These are in the form of (module, function, line index)
    :rtype: list[tuple]
    """
    capture_groups = []
    for index, line in enumerate(lines):
        match = re.search(r"(QtGui|QtCore)\.(\w+)", line)
        if match:
            mod, func = match.groups()
            if "capture_groups" not in locals():
                pass
            capture_groups.append((mod, func, index))
        match = re.search(r"from\s(PySide|PyQt4)\simport\s([\w\s,]+)", line)
        if match:
            mod, imports_ = match.groups()
            capture_groups.append((mod, imports_, index))
    return capture_groups


def test_things(things):
    """
    test_things will filter the matched modules to any QtGui and QtCore modules and replace them with the help of Qt.py.

     # TODO: This should be broken out and optimized. Currently it checks QtGui before QtWidgets. \
         It should use _common_members.

    :param list[tuple] things: List of matches that it found in the file.
        These are in the form of (module, function, line index)
    :return: List of tuples. (Original module, correct module, function, line_index)
    :rtype: list[tuple]
    """
    bad = []
    for mod, func, line_index in things:
        if mod in ["PySide", "PyQt4"]:
            bad.append((mod, func, line_index))
            continue
        try:
            if mod == "QtGui":
                getattr(QtGui, func)
                bad.append((mod, func, line_index))
            elif mod == "QtCore":
                getattr(QtCore, func)
                bad.append((mod, func, line_index))
            else:
                print("What is %s" % mod.strip("\n"))
        except Exception:
            bad.append((mod, func, line_index))
    fixy = []
    for mod, func, line_index in bad:
        if mod in ["PySide", "PyQt4"]:
            correct_mod = "Qt"
            fixy.append((mod, correct_mod, func, line_index))
            continue
        try:
            getattr(QtGui, func)
            correct_mod = "QtGui"
        except:
            try:
                getattr(QtCore, func)
                correct_mod = "QtCore"
            except:
                try:
                    getattr(QtWidgets, func)
                    correct_mod = "QtWidgets"
                except:
                    correct_mod = mod
                    print("Could not fix (\"%s\", \"%s\")" % (mod.strip("\n"), func.strip("\n")))
        fixy.append((mod, correct_mod, func, line_index))
    return fixy


def fix(results, fp, text_lines):
    """
    fix takes a list of tuples from "test_things", a string filepath to the file, and a list of text lines of that file.
    It will use the data gathered in "test_things" to replace specific lines with their correct re-implementations.

    :param list[tuples] results: List of tuples. (Original module, correct module, function, line_index)
    :param str fp: Path to the file that we want to write to.
    :param list[str] text_lines: List of strings that are the lines of the file that was loaded.
    """
    import_index = -1
    required_mods = []
    for orig, good, func, line_index in results:
        if good == "Qt":
            print("Found Qt imports. Line number is %s" % line_index)
            import_index = line_index
            continue
        if good not in required_mods:
            required_mods.append(good)
        print("Fixing line number %d: \"%s\"" % (line_index+1, text_lines[line_index].strip("\n")))
        text_lines[line_index] = text_lines[line_index].replace(orig, good)
    if import_index != -1:
        print("Fixing imports on line %d: \"%s\"" % (import_index+1, text_lines[import_index].strip("\n")))
        text_lines[import_index] = "from dd.runtime import api\napi.load(\"qt_py\")\nfrom Qt import {mods}\n".format(mods=", ".join(required_mods))
    with open(fp, "wb") as fh:
        fh.writelines(text_lines)


def do(path):
    """
    do is the main entrypoint/driver for the qt_py_convert tool. It takes a path which will be read from and written to.
    It should my a single python file.

    :param str path: File path that we will convert.
    """
    with open(path, "rb") as fh:
        data = fh.readlines()
    results = test_things(find_things(data))
    for orig, good, func, line_index in results:
        if orig != good:
            print(
                "Changing to \"%s.%s\" from \"%s.%s\"."
                % (good.strip("\n"), func.strip("\n"), orig.strip("\n"), func.strip("\n"))
            )
    fix(results, path, data)

if __name__ == "__main__":
    import sys
    paths = sys.argv[-1]
    for path in paths.split(","):
        print("--" * 30)
        print("Running on \"%s\"" % path.strip())
        print("--" * 30)
        do(path.strip())
        print("--" * 30)
        print("--" * 30)
        print("")

# TODO: Make this poor POS code better, docstrings, function names, general sensibility, etc
