weibo_terminator_distrbuted
===========================
此项目参考了@jinfagang的WT项目，使用redis实现任务的去重和调度

### Usage:
在完成所有配置(添加accounts, 配置chromedriver路径)后，运行:
```sh
# uid 是待爬取用户id, 如果不指定将使用默认uid
python3 main.py -i uid
```
