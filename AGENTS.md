::ILANG
[TYPE:instructions][PROJECT:vps-deals][LANG:zh]
::STATE{@PROJECT, purpose:真实官方VPS优惠目录, stack:Python标准库加静态HTML}
::RULE{配置唯一真源:.ilang/site.ilang; scraper.py和build.py必须读取}
::ALLOW{修改代码 模板 厂商配置 测试 文档; 用户授权后发布}
::RULE{只抓公开官方页面 feed sitemap; 遵守robots; TLS验证必须开启; 403停止不绕过}
::RULE{每个py文件头包含职责边界的I-Lang注释; 修改后运行python -m unittest discover -s tests和python build.py}
::RULE{改厂商和频率后运行python sync_workflow.py; 所有价格日期必须可追溯; 赠金不等于售价}
::BOUNDARY{never:编优惠 编价格 编佣金 编评价 伪造抓取时间 刷量 cookie注入 品牌词竞价 自买自推|scope:permanent}
::RULE{联盟链接仅在审核通过且验证条款后填写; 无链接用官网; sponsored标签和披露必须保留}
::RULE{不承诺域名年龄带来排名 不承诺永久免费或无人维护 不伪称上线成功}

::RULE{全站历史保留:任何来源抓不到或重新核验失败 不许删除已发布页面 不许重定向首页; 保留历史证据及原复核时间 显示当前未能重新核验; 不计入最新优惠 不输出有效Offer结构化数据; provider与plan继续保留sitemap入口; 首次抓取无历史不得编造历史记录}
