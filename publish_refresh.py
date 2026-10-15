# ::ILANG
# ::STATE{@SELF, role:在最新main的独立工作树重建并发布已抓取数据}
# ::BOUNDARY{never:强推 覆盖发文源文件 伪造抓取时间}
import subprocess
import sys
import tempfile
from pathlib import Path


def run(root, *args, check=True):
    return subprocess.run(args, cwd=root, check=check)


def publish(root, attempts=3):
    root = Path(root).resolve()
    offers = (root / 'data/offers.json').read_bytes()
    for attempt in range(attempts):
        run(root, 'git', 'fetch', 'origin', 'main')
        base = subprocess.check_output(
            ['git', 'rev-parse', 'origin/main'], cwd=root, text=True).strip()
        with tempfile.TemporaryDirectory(prefix='offer-publish-') as directory:
            tree = Path(directory) / 'tree'
            run(root, 'git', 'worktree', 'add', '--detach', str(tree), base)
            try:
                (tree / 'data/offers.json').write_bytes(offers)
                run(tree, sys.executable, 'sync_workflow.py', '--check')
                run(tree, sys.executable, '-m', 'unittest', 'discover', '-s', 'tests')
                run(tree, sys.executable, 'build.py')
                run(tree, 'git', 'add', 'data/offers.json', 'site/')
                diff = run(tree, 'git', 'diff', '--cached', '--quiet', check=False)
                if diff.returncode == 0:
                    print('Latest main already contains these generated results.')
                    return
                if diff.returncode != 1:
                    diff.check_returncode()
                run(tree, 'git', '-c', 'user.name=vps-deals bot', '-c',
                    'user.email=41898282+github-actions[bot]@users.noreply.github.com',
                    'commit', '-m', 'Refresh official sources and static pages')
                pushed = run(tree, 'git', 'push', 'origin', 'HEAD:main', check=False)
                if pushed.returncode == 0:
                    return
                run(root, 'git', 'fetch', 'origin', 'main')
                latest = subprocess.check_output(
                    ['git', 'rev-parse', 'origin/main'], cwd=root, text=True).strip()
                if latest == base:
                    pushed.check_returncode()
                print(f'Main changed during publication; rebuilding ({attempt + 1}/{attempts}).')
            finally:
                run(root, 'git', 'worktree', 'remove', '--force', str(tree))
    raise RuntimeError('Main kept changing; no forced push was attempted. Re-run the workflow.')


if __name__ == '__main__':
    publish(Path(__file__).parent)
