import argparse
import glob
import re
import os
import sys
from subprocess import Popen

point_dict = {
    "cpprefjp/typo": 1,
    "cpprefjp/link": 2,
    "cpprefjp/addref": 20,
    "cpprefjp/addlang": 20,
    "cpprefjp/addpage": 20,
    "cpprefjp/fixs": 2,
    "cpprefjp/fixm": 5,
    "cpprefjp/fixl": 10,
    "cpprefjp/compiler": 2,
    "boostjp/typo": 1,
    "boostjp/link": 2,
    "boostjp/releases": 5,
    "boostjp/releasem": 10,
    "boostjp/releasel": 20,
    "boostjp/fixs": 2,
    "boostjp/fixm": 5,
    "boostjp/addrefs": 10,
    "boostjp/addrefm": 20,
    "tool/fixbug": 30,
    "tool/improves": 10,
    "tool/improvem": 30,
    "tool/improvem": 50,
    "tool/updatelib": 20,
    "tool/updatelang": 10,
    "tool/updatelang": 30,
    "tool/updatelang": 50,
    "tool/adds": 30,
    "tool/addm": 50,
    "tool/addl": 100,
}

def stats_contribution(text: str, filename: str, exclude_users: list[str]) -> set[str]:
    user_name: str | None = None
    user_point = 0
    commit_set = set()

    users = dict()
    for line in text.split("\n"):
        m = re.fullmatch(r'## (.*?)', line)
        if m:
            m = re.fullmatch(r'\[(.*?)\]\((.*?)\)', m.group(1))
            user_name = m.group(1)
            user_point = 0
            continue

        if not user_name:
            continue

        if line.startswith("| ["):
            cols = line.split("|")

            commits = cols[1].split(",")
            for commit in commits:
                m = re.fullmatch(r'\[(.*?)\]\((.*?)/commit/(.*?)\)', commit.strip())
                full_commit_id = m.group(3)
                commit_set.add(full_commit_id)

            points = cols[2].strip().split(",")
            for point in points:
                if len(point) == 0:
                    continue

                point_values = point.split(":")
                point_name = point_values[0].strip()
                try:
                    point_quantity = int(point_values[1].strip())
                except:
                    print("invalid quantity: {}".format(point))
                    raise

                point_value = point_dict.get(point_name)
                if not point_value:
                    raise KeyError("{}: invalid point tag `{}`".format(filename, point_name))
                user_point += point_value * point_quantity
            users[user_name] = user_point

    sum_point = 0
    for name, point in users.items():
        if name in exclude_users:
            continue
        sum_point += point

    print("| user | points | rate |")
    print("|------|--------|------|")
    for name, point in sorted(users.items(), key=lambda item: item[1], reverse=True):
        if name in exclude_users:
            continue
        print("| @{} | {} | {:.3}% |".format(name, point, point / sum_point * 100.0))
    return commit_set

def check_commit_set(commit_set: set[str]) -> None:
    repos = [
        "cpprefjp/site",
        "cpprefjp/site_generator",
        "cpprefjp/kunai",
        "cpprefjp/kunai_config",
        "cpprefjp/crsearch",
        "cpprefjp/markdown_to_html",
        "boostjp/site",
    ]

    commit_log_set = set()
    for repo in repos:
        wd = os.getcwd()
        command = "git log --after \'2023-01-01\' --pretty=oneline --no-merges".split(" ")
        os.chdir(repo)
        proc = Popen(command, stdin=-1,stdout=-1,stderr=-1)
        out, err = proc.communicate()
        if len(err) > 0:
            print(err)
            return
        os.chdir(wd)

        for line in out.decode().split("\n"):
            if len(line) <= 0:
                continue
            cols = line.split(" ")
            full_commit_id = cols[0]
            commit_log_set.add(full_commit_id)

    diff = commit_log_set - commit_set
    if len(diff) > 0:
        print("unstats commits: {}\n{}".format(len(diff), diff))

if __name__ == '__main__':
    argparser = argparse.ArgumentParser(description="")
    argparser.add_argument("--exclude-users",
                           dest='exclude_users_str',
                           type=str,
                           default="",
                           help="comma separated userid list")
    args = argparser.parse_args()

    exclude_users = args.exclude_users_str.split(",")

    commit_set = set()
    for p in sorted(list(glob.glob("cpprefjp/site/start_editing/*.md", recursive=True))):
        filename = os.path.basename(p)
        if not filename.startswith("contribution_stats_"):
            continue

        with open(p) as f:
            text = f.read()

        commit_set = commit_set.union(stats_contribution(text, p, exclude_users))

    check_commit_set(commit_set)
