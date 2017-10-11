#! /usr/bin/python3
r"""generate amalgamation.py.

Usage:
  generate.py amalgamation
  generate.py makefile
  generate.py concatenate --filename <filename> --base <base> [--] <list>...

Options:
  -h --help      _o/ .
  --version      \o_ .
  --filename <filename>  \o/
  --base <base>  \o/
"""
import argparse
import sys

from docopt import docopt
from path import Path

from tools import *


def parse_command_line():
    args = docopt(__doc__, version='0.2')
    return args


def amalgamation():
    """
        Write concatenated Dockerfile in function of all Dockerfile in the repository
        Only if docker file have dependency
    """
    deps = extract_dependence()

    for image_names in deps:
        # we don't need to generate amalgamation if no dependencies
        if len(image_names) <= 1:
            continue

        filename = '../super/%s.super' % imagename_to_filename(image_names[0])
        Path(filename).parent.makedirs_p()

        firstloop = True
        with open(filename, "w") as file_out:
            for image_name in image_names[::-1]:
                if not firstloop:
                    file_out.write("\n# ==============================================================================\n")
                    file_out.write("# %s\n" % imagename_to_filename(image_name))

                if Path("../" + imagename_to_filename(image_name)).exists():
                    _filename = "../" + imagename_to_filename(image_name)
                else:
                    _filename = "../super/" + imagename_to_filename(image_name)

                with open(_filename, "r") as file_in:
                    for i in file_in:
                        match = re.search(r"FROM|LABEL maintainer", i)
                        if match and not firstloop:
                            continue
                        file_out.write(i)
                
                firstloop = False


def concatenate_image(filename, base, image_list):

    with open(filename, "w") as file_out:
        file_out.write("FROM %s\n" % base)
        file_out.write('LABEL maintainer="Erwan BERNARD https://github.com/edmBernard/DockerFiles"\n\n')
        file_out.write("# " + " ".join(sys.argv) + "\n")

        for image_name in image_list:
            file_out.write("\n# ==============================================================================\n")
            file_out.write("# %s\n" % imagename_to_filename(image_name))
            print("../%s" % (imagename_to_filename(image_name)))
            with open("../%s" % imagename_to_filename(image_name), "r") as file_in:
                for i in file_in:
                    match = re.search(r"FROM|LABEL maintainer", i)
                    if match:
                        continue
                    file_out.write(i)


def makefile():
    """
        Write Makefile in function of all Dockerfile in the repository
    """

    graph = extract_dependence()
    sorted_graph = sorted(graph, key=lambda t: (-len(t), t[0]))
    image_list = [i[0] for i in sorted_graph]
    deps_list = [i[1:] for i in sorted_graph]
    filename_list = [imagename_to_filename(i) if Path("../" + imagename_to_filename(i)).exists() else "super/" + imagename_to_filename(i) for i in image_list]

    with open("../Makefile", "w") as fl:
        fl.write("NOCACHE=OFF\n")
        fl.write("\n")
        fl.write("ifeq ($(NOCACHE),ON)\n")
        fl.write("\targ_nocache=--no-cache\n")
        fl.write("else\n")
        fl.write("\targ_nocache=\n")
        fl.write("endif\n\n\n")

        fl.write(".PHONY: all all_cpu all_gpu clean clean_cpu clean_gpu ")
        fl.write(" ".join(image_list) + " ")
        fl.write(" ".join(["clean_%s" % i for i in image_list]))
        fl.write("\n\n\n")

        fl.write("all: all_cpu all_gpu\n\n")
        fl.write("all_cpu: ")
        fl.write(" ".join([i for i in image_list[::-1] if "cpu" in i]))
        fl.write("\n\n")
        fl.write("all_gpu: ")
        fl.write(" ".join([i for i in image_list[::-1] if "gpu" in i]))
        fl.write("\n\n\n")

        fl.write("clean: ")
        fl.write(" ".join(["clean_%s" % i for i in image_list]))
        fl.write("\n\n")
        fl.write("clean_cpu: ")
        fl.write(" ".join(["clean_%s" % i for i in image_list if "cpu" in i]))
        fl.write("\n\n")
        fl.write("clean_gpu: ")
        fl.write(" ".join(["clean_%s" % i for i in image_list if "gpu" in i]))
        fl.write("\n\n\n")

        for i, f, d in zip(image_list, filename_list, deps_list):
            fl.write("%s: " % i)
            fl.write(" ".join(d[:1]))
            if "gpu" in i:
                fl.write("\n\tnvidia-docker build $(arg_nocache) -t %s -f %s %s\n\n" % (i, f, f.split("/")[0]))
            else:
                fl.write("\n\tdocker build $(arg_nocache) -t %s -f %s %s\n\n" % (i, f, f.split("/")[0]))

            fl.write("clean_%s: " % i)
            fl.write(" ".join(["clean_%s" % ti for ti, td in zip(image_list, deps_list) if i in td]))
            fl.write("""\n\tif [ "$$(docker images -q --filter=reference='%s')" != "" ]; then docker rmi %s; else echo "0"; fi\n\n""" % (i, i))


if __name__ == '__main__':
    clo = parse_command_line()

    if clo["amalgamation"]:
        print("Amalgamation Generation")
        amalgamation()
    elif clo["makefile"]:
        print("Makefile Generation")
        makefile()
    elif clo["concatenate"]:
        print("Concatenate image")
        concatenate_image(clo["--filename"], clo["--base"] + ":latest"*(":" not in clo["--base"]), clo["<list>"])

    print("Generation Done")