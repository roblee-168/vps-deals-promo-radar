# ::ILANG
# ::STATE{@SELF, role:用本地Git远端验证刷新与发文并发时不丢页面}
# ::BOUNDARY{never:访问真实远端 修改生产数据}
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import publish_refresh


class PublishRefreshTests(unittest.TestCase):
    def test_rebuild_after_concurrent_article_push(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            remote, seed, worker, author = [root / n for n in ('remote.git', 'seed', 'worker', 'author')]
            def git(path, *args):
                subprocess.run(['git', *args], cwd=path, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            git(root, 'init', '--bare', str(remote))
            git(root, 'init', '-b', 'main', str(seed))
            git(seed, 'config', 'user.name', 'Test')
            git(seed, 'config', 'user.email', 'test@example.invalid')
            (seed / 'data').mkdir()
            (seed / 'site').mkdir()
            (seed / 'tests').mkdir()
            (seed / 'tests/test_fixture.py').write_text('import unittest\nclass Fixture(unittest.TestCase):\n    def test_valid(self): self.assertTrue(True)\n')
            (seed / 'data/offers.json').write_text('old')
            (seed / 'site/index.html').write_text('old')
            (seed / 'sync_workflow.py').write_text('')
            (seed / 'build.py').write_text("from pathlib import Path\nPath('site/index.html').write_text(Path('data/offers.json').read_text())\nfor p in Path('.').glob('article-*.txt'): Path('site',p.name).write_text(p.read_text())\n")
            git(seed, 'add', '.')
            git(seed, 'commit', '-m', 'baseline')
            git(seed, 'remote', 'add', 'origin', str(remote))
            git(seed, 'push', 'origin', 'main')
            git(root, 'clone', '-b', 'main', str(remote), str(worker))
            git(root, 'clone', '-b', 'main', str(remote), str(author))
            git(author, 'config', 'user.name', 'Author')
            git(author, 'config', 'user.email', 'author@example.invalid')
            (worker / 'data/offers.json').write_text('fresh')
            original = publish_refresh.run
            pushes = []
            def racing_run(path, *args, **kwargs):
                if args[:2] == ('git', 'push'):
                    pushes.append(1)
                    if len(pushes) == 1:
                        (author / 'article-new.txt').write_text('new article preserved')
                        git(author, 'add', '.')
                        git(author, 'commit', '-m', 'concurrent article')
                        git(author, 'push', 'origin', 'main')
                return original(path, *args, **kwargs)
            with patch.object(publish_refresh, 'run', side_effect=racing_run):
                publish_refresh.publish(worker)
            self.assertEqual(len(pushes), 2)
            git(author, 'pull', '--ff-only')
            self.assertEqual((author / 'site/article-new.txt').read_text(), 'new article preserved')
            self.assertEqual((author / 'data/offers.json').read_text(), 'fresh')
            self.assertEqual((author / 'site/index.html').read_text(), 'fresh')
            self.assertFalse(list(root.glob('offer-publish-*')))
