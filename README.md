# arXiv学术论文分析与筛选工具

[English](./README.en.md) | [中文](./README.md)

这是一个完整的学术论文分析工作流工具，专注于识别和筛选arXiv上已被顶级期刊/会议接收或发表的AI论文。整个工作流包括：

1. **数据获取**：通过影刀RPA自动化工具从arXiv爬取AI分类下的论文信息
2. **论文筛选**：分析论文的Comments字段，识别已被接收(accepted)或发表(published)在顶级期刊/会议上的论文
3. **质量评估**：基于中国计算机学会(CCF)推荐的[国际学术刊物目录](https://www.ccf.org.cn/Academic_Evaluation/AI/)进行筛选和分级
4. **关键词匹配**：对已筛选出的高质量论文进行个人关键词匹配，进一步标记特定研究领域的论文

本工具适用于研究人员快速发现最新的高质量AI研究成果，特别是那些已被顶级会议/期刊接收但尚未正式发表的论文。

## 测试数据

我们将提供测试数据包，包含以下内容：
1. arXiv论文信息样本数据
2. CCF推荐国际学术刊物参考列表
3. 示例关键词配置

您可以使用这些测试数据来熟悉工具的功能和工作流程。

## 主要功能

该工具主要执行两步分析：

1. **第一步分析**：查找论文数据中包含"Comments"的记录，并与刊物名称进行匹配
   - 在论文数据的第三列（C列-说明信息）中查找包含"Comments"的记录
   - **匹配逻辑**：
     - 优先检查说明信息中是否包含参考信息中的"刊物全称"
     - 如未命中，尝试匹配全英文大写的"刊物名称"
     - 尝试匹配CVPR2025等特殊格式的会议名称缩写
     - 尝试从"Accepted at/in/to [会议名称]"等模式中提取会议名称并匹配
     - 如果都未命中，则不选中该论文
   - 记录匹配结果及匹配类型（刊物全称/刊物简称/刊物简称带年份/会议名称匹配/会议缩写匹配）

2. **第二步分析**：检查匹配记录的标题是否包含特定关键词
   - 从"关键词整理"表中获取英文关键词
   - 检查论文标题是否包含这些关键词（精确匹配但忽略大小写）
   - 如有匹配，在结果中显示命中的关键词

## 配置说明

程序使用JSON格式的配置文件（`config.json`）存储文件路径和工作表名称：

```json
{
    "file_paths": {
        "paper_info": "C:\\Users\\panhe\\Desktop\\论文信息.xlsx",
        "reference_info": "C:\\Users\\panhe\\Desktop\\中国计算机学会推荐国际学术刊物&会议.xlsx"
    },
    "sheet_names": {
        "publication_category": "出版物分类",
        "keywords": "关键词整理"
    }
}
```

您可以根据实际情况修改配置文件中的路径和工作表名称。

## 使用方法

1. 确保您已安装Python环境和必要的依赖库（pandas、openpyxl）
2. 修改`config.json`文件，确保文件路径正确
3. 运行脚本：

```bash
python academic_paper_analyzer.py
```

## 输出结果

程序会在控制台显示分析结果，同时将完整结果保存到Excel文件：

1. 第一步分析结果：显示匹配的论文、对应的出版物分类和匹配类型
2. 第二步分析结果：显示标题中包含特定关键词的论文
3. 所有结果保存在带有时间戳的`analysis_results_[时间戳].xlsx`文件中

## 数据要求

1. **论文信息Excel文件**：
   - **没有表头**，直接从第一行开始是数据
   - A列 - 论文名称
   - B列 - 作者信息
   - C列 - 说明信息（可能包含"Comments"等关键字）
   - D列 - PDF地址

2. **参考信息Excel文件**：
   - 有表头
   - 必须包含"刊物名称"和"刊物全称"列
   - "刊物名称"列中的全英文大写名称会用于第二优先级匹配
   - "关键词整理"表中应有"英文关键词"列，用于第二步分析

## 会议映射配置

程序内置了一些会议名称和缩写的映射关系，以便更准确地识别会议名称：

```python
CONFERENCE_MAPPINGS = {
    "IJCNN": "International Joint Conference on Neural Networks",
    "NAACL": "Annual Meeting of the North American Chapter of the Association for Computational Linguistics",
    "ACL": "Annual Meeting of the Association for Computational Linguistics",
    "ICCV": "International Conference on Computer Vision",
    "CVPR": "IEEE/CVF Conference on Computer Vision and Pattern Recognition",
    "EMNLP": "Conference on Empirical Methods in Natural Language Processing",
    "ICML": "International Conference on Machine Learning",
    "NeurIPS": "Annual Conference on Neural Information Processing Systems",
    "AICCSA": "ACS/IEEE International Conference on Computer Systems and Applications"
}
```

您可以在代码中添加更多的会议映射关系。

## 匹配逻辑详解

1. **优先级1：刊物全称匹配**
   - 检查论文说明信息（C列）中是否包含参考信息中的任何"刊物全称"
   - 匹配不区分大小写，但必须是完整包含
   - 匹配类型：`刊物全称(精确)`

2. **优先级2：刊物名称匹配**
   - 仅当优先级1未匹配成功时执行
   - 仅匹配全部为英文大写的刊物名称（如"TPAMI", "IJCV"）
   - 匹配区分大小写，必须完全匹配
   - 匹配类型：`刊物简称(精确)`

3. **优先级3：刊物简称带年份匹配**
   - 仅当前两种匹配未成功时执行
   - 匹配如"CVPR2025"这样的格式（无空格）
   - 匹配类型：`刊物简称(带年份)`

4. **优先级4：会议名称/缩写匹配**
   - 尝试从文本中提取可能的会议名称
   - 将提取的名称与内置的会议映射关系进行匹配
   - 匹配类型：`会议名称匹配`或`会议缩写匹配`

5. **不匹配的情况**
   - 如果论文说明信息中没有包含"Comments"
   - 如果论文说明信息中没有匹配到任何会议或期刊名称

## 关键词匹配说明

在第二步分析中，关键词匹配有以下特点：
- 使用"关键词整理"表中的"英文关键词"列进行匹配
- 使用精确词边界匹配，确保只匹配完整的单词，而不是单词的一部分
- 匹配时忽略大小写，因此"Neural"可以匹配到"neural"或"NEURAL"
- 多个关键词用逗号分隔

## 故障排除

如果遇到以下问题，请尝试相应的解决方法：

1. **找不到工作表**：检查Excel文件中的实际工作表名称，并更新`config.json`中的配置
2. **列名不匹配**：查看Excel文件的实际列名，修改代码中的列名引用
3. **文件路径错误**：确保文件路径正确，注意Windows路径中使用双反斜杠或原始字符串
4. **数据格式问题**：确保论文信息Excel没有表头，而参考信息Excel有表头
5. **会议识别问题**：如果某些会议名称无法识别，可以在代码中的`CONFERENCE_MAPPINGS`中添加相应的映射

## 最近更新

- 增强了对会议缩写格式的识别能力，现在可以识别如"CVPR2025"这样没有空格的格式
- 改进了关键词匹配逻辑，使用"英文关键词"列进行精确匹配
- 修复了部分会议无法识别的问题

## 数据来源

本工具使用的论文数据是通过影刀RPA自动爬取arXiv上AI分类下的论文获得的。具体爬取方式如下：

- 使用了影刀RPA机器人自动化工具进行数据采集
- 机器人会自动访问arXiv网站，获取AI分类下的最新论文信息
- 提取的数据包括论文标题、作者、摘要、Comments信息以及PDF链接
- 数据会自动保存为Excel格式，供本分析工具使用

如需使用或修改爬取机器人，可以通过以下链接访问：[arXiv论文爬取机器人](https://api.winrobot360.com/redirect/robot/share?inviteKey=4fa722bd79b12b1f)

如果需要修改爬取网页或修改爬取数量，可以打开影刀RPA软件重新编辑流程。

## 环境要求

- Python 3.6+
- pandas
