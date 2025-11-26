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
    "tool/improvel": 50,
    "tool/updatelib": 20,
    "tool/security": 50,
    "tool/updatelang": 10,
    "tool/updatelang": 30,
    "tool/updatelang": 50,
    "tool/adds": 30,
    "tool/addm": 50,
    "tool/addl": 100,
    "ignore": 0,
}

target_repos = [
    "cpprefjp/site",
    "cpprefjp/site_generator",
    "cpprefjp/kunai",
    "cpprefjp/kunai_config",
    "cpprefjp/crsearch",
    "cpprefjp/markdown_to_html",
    "boostjp/site",
]

def stats_contribution(text: str,
                       filename: str,
                       year: int,
                       target_year: int,
                       receive_users: list[str],
                       exclude_users: list[str],
                       max_user_point_dict: dict[str, int],
                       additional_user_point_dict: dict[str, int]) -> dict[str, set[str]]:
    def is_active_user(name: str) -> bool:
        if name in exclude_users:
            return False
        if len(receive_users) == 0:
            return True
        return name in receive_users;

    user_name: str | None = None
    user_point = 0
    commit_dict: dict[str, set[str]] = dict(set())

    is_target_year = year == target_year

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

            for m in re.finditer(r'\[commit (.*?)\]', cols[1].strip()):
                c = m[1].split(", ")
                repo = c[0]
                commit_ids = set()
                for id in c[1:]:
                    id = id.strip()
                    if len(id) == 0:
                        continue
                    if len(id) < 7:
                        raise Exception("{}: {} (len:{}) commit-id length should be greater than or equal 7".format(filename, id, len(id)))
                    commit_ids.add(id)

                if repo in commit_dict:
                    commit_dict[repo] |= commit_ids
                else:
                    commit_dict[repo] = commit_ids

            points = cols[2].strip().split(",")
            for point in points:
                if len(point) == 0:
                    continue

                point_values = point.split(":")
                point_name = point_values[0].strip()
                if len(point_values) != 2:
                    if point_name != "ignore":
                        raise Exception("{}: quantity is empty: {}".format(filename, point))

                point_value = point_values[1].strip() if len(point_values) == 2 else "1"
                if len(point_value) == 0:
                    raise Exception("{}: invalid quantity: {}".format(filename, point))

                point_quantity = int(point_value)
                point_value = point_dict.get(point_name)
                if point_value is None:
                    raise KeyError("{}: invalid point tag `{}`, line:{}".format(filename, point_name, line))
                user_point += point_value * point_quantity
            users[user_name] = user_point

    base_sum_point = 0
    sum_point = 0
    for name, point in users.items():
        base_sum_point += point
        if is_active_user(name):
            user_point = point
            if name in additional_user_point_dict:
                user_point += additional_user_point_dict[name]
            if name in max_user_point_dict:
                user_point = min(max_user_point_dict[name], point)
            sum_point += user_point

    if is_target_year:
        print("| No. | user | base point | point | base rate | rate |")
        print("|-----|------|------------|-------|-----------|------|")
        number = 0
        acc_number = 0
        prev_point = 0
        for name, point in sorted(users.items(), key=lambda item: item[1], reverse=True):
            base_rate = point / base_sum_point * 100.0
            user_point = point
            if name in additional_user_point_dict:
                user_point += additional_user_point_dict[name]
            if name in max_user_point_dict:
                user_point = min(max_user_point_dict[name], point)

            if prev_point == 0 or point != prev_point:
                number += 1 + acc_number
                acc_number = 0
            else:
                acc_number += 1
            prev_point = point

            rate = (user_point / sum_point * 100.0) if is_active_user(name) else 0.0
            print("| {} | @{} | {} | {} | {:.3}% | {:.3}% |".format(
                number,
                name,
                point,
                user_point,
                base_rate,
                rate))
    return commit_dict

def diff_commit_set(commit_log_set: set[str], stats_commit_set: set[str]) -> set[str]:
    diff = commit_log_set - stats_commit_set
    if len(diff) > 0:
        remove_commit_set: set[str] = set()
        for commit in diff:
            for stats_commit in stats_commit_set:
                if stats_commit.startswith(commit):
                    remove_commit_set.add(commit)
                    break
        for commit in remove_commit_set:
            diff.remove(commit)
    return diff

def check_commit_dict(commit_dict: dict[str, set[str]]) -> None:
    for repo in commit_dict.keys():
        if repo not in target_repos:
            raise Exception("unknown repo name:{}".format(repo))

    commit_log_set = set()
    for repo in target_repos:
        wd = os.getcwd()
        command = "git log --after \'2023-01-01\' --pretty=oneline --no-merges".split(" ")
        os.chdir(repo)
        proc = Popen(command, stdin=-1,stdout=-1,stderr=-1)
        out, err = proc.communicate()
        if len(err) > 0:
            print(err)
            return
        os.chdir(wd)

        commit_set: set[str] = set()
        for line in out.decode().split("\n"):
            if len(line) <= 0:
                continue
            cols = line.split(" ")
            commit_id = cols[0][:7]
            if len(commit_id) != 7:
                raise Exception("git log: {} commit-id length should be 7".format(commit_id))
            commit_set.add(commit_id)

        repo_commit_set: set[str] = commit_dict[repo] if repo in commit_dict else set()
        diff = diff_commit_set(commit_set, repo_commit_set)
        if len(diff) > 0:
            print("unstats commits {}: {}\n{}".format(repo, len(diff), diff))

if __name__ == '__main__':
    argparser = argparse.ArgumentParser(description="")
    argparser.add_argument("--year",
                           dest='target_year',
                           type=int,
                           default=0,
                           help="target year")
    argparser.add_argument("--exclude-users",
                           dest='exclude_users_str',
                           type=str,
                           default="",
                           help="comma separated userid list")
    argparser.add_argument("--receive-users",
                           dest='receive_users_str',
                           type=str,
                           default="",
                           help="comma separated userid list")
    argparser.add_argument("--max-user-points",
                           dest='max_user_points_str',
                           type=str,
                           default="",
                           help="comma separated max point list")
    argparser.add_argument("--additional-user-points",
                           dest='additional_user_points_str',
                           type=str,
                           default="",
                           help="comma separated additional point list")
    args = argparser.parse_args()

    if args.target_year == 0:
        raise Exception("you must specify `--year N` option")

    receive_users = [] if len(args.receive_users_str) == 0 else args.receive_users_str.split(",")
    exclude_users = [] if len(args.exclude_users_str) == 0 else args.exclude_users_str.split(",")

    max_user_points = args.max_user_points_str.split(",")
    max_user_point_dict = dict()
    for s in max_user_points:
        if len(s) == 0:
            continue
        values = s.split("=")
        max_user_point_dict[values[0]] = int(values[1])

    additional_user_points = args.additional_user_points_str.split(",")
    additional_user_point_dict = dict()
    for s in additional_user_points:
        if len(s) == 0:
            continue
        values = s.split("=")
        additional_user_point_dict[values[0]] = int(values[1])

    commit_dict: dict[str, set[str]] = dict(set())
    for p in sorted(list(glob.glob("cpprefjp/site/start_editing/*.md", recursive=True))):
        filename = os.path.basename(p)
        m = re.fullmatch(r"contribution_stats_([0-9]*?)\.md", filename)
        if not m:
            continue

        year = int(m[1])
        with open(p) as f:
            text = f.read()

        commits = stats_contribution(
            text,
            p,
            year,
            args.target_year,
            receive_users,
            exclude_users,
            max_user_point_dict,
            additional_user_point_dict
        )
        for repo in target_repos:
            repo_commits: set[str] = commits[repo] if repo in commits else set()

            if repo in commit_dict:
                commit_dict[repo] |= repo_commits
            else:
                commit_dict[repo] = repo_commits

    check_commit_dict(commit_dict)
