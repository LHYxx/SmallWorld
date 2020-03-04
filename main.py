import requests
from bs4 import BeautifulSoup
import os
import copy

header = {
	"Accept": 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
	'User-Agent': 'Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.122 Safari/537.36'
}


global_url_list = []  # 全局url
global_exists_url_list = []  # 全局已爬url
global_person_list = []  # 全局 person对象 列表
global_person_dict = {}  # 全局 person对象 词典。 {name: person}

crawled_person_file = 'persons.txt'  # 爬取的人物数据文件名
crawled_relation_file = 'relations.txt'  # 关系数据文件名

cleaned_person_file = 'cleaned_person_file.txt'  # 清洗后的人物数据文件；
cleaned_relation_file = 'cleaned_relation_file.txt'  # 清洗后的关系数据文件；

PERSON_NUM_TO_CRAWL = 50000  # 爬取的人物上限 

class Relation():
	def __init__(self, source, target, relation, t='resolved'):
		self.source = source
		self.target = target
		self.relation = relation
		self.t = t

	def to_string(self):
		s = "source: '{}', target: '{}', 'rela': '{}', type: '{}'".format(self.source, self.target, self.relation, self.t)
		return "{" + s + "},\n"


class Person(object):
	'''人物 类'''
	def __init__(self, ID, name=None, url=None):
		self.id = ID
		self.name = name  # 名字
		self.relation = dict()  # 关系 {relation: [name1, name2 ...]}
		self.pic = None  # 封面
		self.url = url  # url

	def add_relation(self, relation, name):
		'''person.add_relation(relation, name)
		relation: (str) 关系
		name：（str）名字'''
		if relation not in self.relation.keys():
			self.relation[relation] = [name]
		else:
			if name not in self.relation[relation]:
				self.relation[relation].append(name)
			else:
				print("{}-{}已存在".format(relation, name))

	def add_pic(self, pic):
		self.pic = pic

	def to_string(self):
		print("name:{}".format(self.name))
		print("relations:{}".format(self.relation))

	def save_file(self):
		'''将人物信息保存到文件，如果文件不存在则创建，如果已存在则追加'''
		with open(crawled_person_file, 'a', encoding='utf-8') as f:
			f.write("{}\n".format(self.id))
			f.write("{}\n".format(self.name))
			f.write("{}\n".format(self.pic))
			f.write("{}\n".format(self.url))
			for relation, name in self.relation.items():
				f.write("{}:{}\n".format(relation, " ".join(name)))
			f.write("\n")
		print("save {} done.".format(self.name))

	def save_relations(self):
		'''将关系保存到文件，如果文件不存在则创建，如果文件已存在则追加'''
		relations = []
		with open(crawled_relation_file, 'a', encoding='utf-8') as f:
			for relation, names in self.relation.items():
				for name in names:
					f.write(Relation(self.name, name, relation).to_string())

	def __eq__(self, other):
		if isinstance(other, Person):
			return self.id == other.id
		else:
			return self.id == other

	def __str__(self):
		return self.name

	def relation_with(self, person_name):
		'''给定一个person，判断与自己的关系。如果没有直接关系，返回None'''
		if self.name == person_name:
			return 'self'
		for relation, names in self.relation.items():
			for name in names:
				if person_name == name:
					return relation
		return None


def get_person(url):
	'''爬取url对应人物的数据
	返回person对象'''
	html = requests.get(url, headers=header, timeout=10)
	html = html.content
	soup = BeautifulSoup(html, 'html.parser')
	name = soup.find('h1').text.replace(' ', '·').upper()
	print(name)
	if '错误' in name:
		print("{} error! skip!".format(url))
		return
	ID = url.split('/')[-1]
	cur_person = Person(name, ID, url)
	
	# 定位relations部分
	# 如果该页面有 slider_relations，直接定位到人物关系
	relations = soup.find(id='slider_relations')

	if relations is None:  # 如果没有slider_relations项
		relations = soup.select('ul.slider.maqueeCanvas')
		if len(relations) == 0:  # 没有关系，爬虫终止
			if url not in global_exists_url_list:
				cur_person.save_file()
			return
		if relations[0].parent['id'] == 'slider_works':  # 如果爬到的是作品而不是人物关系
			if url not in global_exists_url_list:
				cur_person.save_file()
			return
		relations = soup.select('ul.slider.maqueeCanvas')[0].find_all('li')
	else:  # 如果有slider_relations
		relations = relations.select('ul.slider.maqueeCanvas')[0].find_all('li')
		if len(relations) == 0:  # 没有关系，爬虫终止
			if url not in global_exists_url_list:
				cur_person.save_file()
			return
	# 定位relation部分 END

	# 为用户添加关系
	for person in relations:
		pic = person.img['src']
		ID = person.a['href'].split('/')[-1]
		next_url = "https://baike.baidu.com" + person.a['href']
		if next_url not in global_url_list and next_url != "https://baike.baidu.com":  # 过滤掉重复人物
			global_url_list.append(next_url)
		person = person.div
		# print(person)
		name = person['title']
		
		if person.span is None:
			relation = person.text.replace(name, '')
		else:
			relation = person.span.text
		cur_person.add_relation(relation, ID)
		cur_person.add_pic(pic)
		

	# 为用户添加关系 END
		
	if cur_person.url in global_exists_url_list:
		print("{} exists, skip..".format(person.name))
	else:  # 保存人物信息
		cur_person.save_file()
		cur_person.save_relations()
	return cur_person


def clean_data(srcfile, outputfile):
	'''
	清理数据
	将只在关系中出现的人物，但是全局名单中没有的人物删除
	英文名大写
	srcfile：初始爬下来的数据文件
	outputfile：清理后的输出文件
	'''
	init(srcfile)  # 从文件读取人物数据
	# 对每个人的关系进行清理，如果关系中的人物没有在全局名单中，则删除
	for person in global_person_list:
		person.name = person.name.upper()
		relations = person.relation
		temp_relations = copy.deepcopy(relations)
		for relation, ids in relations.items():
			temp_relation = []
			temp = [x for x in ids]
			for ID in ids:
				if Person(ID) not in global_person_list:
					temp.remove(ID)
					if len(temp) == 0:
						temp_relation.append(relation)
			temp_relations[relation] = temp
			for to_delete_relation in temp_relation:
				temp_relations.pop(to_delete_relation)
		person.relation = temp_relations
	# 保存清理后的文件
	with open(outputfile, 'w', encoding='utf-8') as f:
		for person in global_person_list:
			f.write("{}\n".format(person.name.upper()))
			f.write("{}\n".format(person.id))
			f.write("{}\n".format(person.pic))
			f.write("{}\n".format(person.url))
			for relation, name in person.relation.items():
				f.write("{}:{}\n".format(relation, " ".join(name)))
			f.write("\n")

def clean_relation_data(person_info_file, srcfile, outputfile):
	'''
	清洗 关系数据 文件
	将只在关系中出现而没有在全局名单中出现的人物删除
	'''
	init(person_info_file)
	text = []
	with open(srcfile, 'r', encoding='utf-8') as f:
		for line in f:
			sline = line.split("'")
			source = sline[1]
			target = sline[3]
			if Person(source) not in global_person_list or Person(target) not in global_person_list:
				print(text)
				continue
			text.append(line)
	with open(outputfile, 'w', encoding='utf-8') as f:
		f.write("".join(text))
	print("done!")

def init(initfile):
	'''从initfile文件 读取人物数据'''
	if not os.path.exists(initfile):
		print('无初始数据，重新开始')
		return
	text = []
	with open(initfile, 'r', encoding='utf-8') as f:
		for line in f:
			text.append(line.strip())
			if line == '\n':
				ID = text[1]
				name = text[0]
				# print(name)
				pic = text[2]
				url = text[3]
				person = Person(ID, name, url)
				person.add_pic(pic)
				if len(text) > 4:
					for relations in text[4:-1]:
						# print(relations)
						relation, names = relations.split(":")
						names = names.split()
						for name in names:
							person.add_relation(relation, name)
				if person.id not in global_person_dict.keys():
					global_person_dict[person.id] = person
					# print(person.name)
				global_person_list.append(person)
				global_exists_url_list.append(person.url)
				text = []
	print("init done!")

def download_data(starturl=r'https://baike.baidu.com/item/%E9%B2%81%E8%BF%85/36231'):
	'''从百度百科上扒数据'''
	# url = r'https://baike.baidu.com/item/%E9%87%91%E9%93%81%E9%9C%96/816268'
	# get_person(url)
	init(cleaned_person_file)
	count = PERSON_NUM_TO_CRAWL
	person_list = []
	relation_list = []
	strat_person = starturl
	global_url_list.append(strat_person)  # 保存全局url
	for i, url in enumerate(global_url_list):
		print("{}: {}".format(i, url))
		person = get_person(url)
		if i > count:
			break
	print("done!")


def check_person(cur_person, target, checked_person_list, uncheck_person_list, father_person_list, relation_path):
	'''将person对象的关系dic转化为person对象列表'''
	checked_person_list.append(cur_person)  # 将检查的 人物 添加到 已检查列表
	if cur_person == target:  # 搜索到目标
		return True

	# 将当前人物的朋友加到待检查列表
	for relation, ids in cur_person.relation.items():
		for ID in ids:
			person = global_person_dict[ID]
			if person not in checked_person_list and person not in uncheck_person_list:  # 搜索人物去重，防止同一人物重复搜索。
				# print(person.id, person.name)
				uncheck_person_list.append(person)
				father_person_list.append(cur_person)
				relation_path.append(cur_person.relation_with(person))
	
	uncheck_person_list.remove(cur_person)  # 从 待检查列表 移除 当前人物
	return False

def BFSsearch(source, target):
	'''
	搜索关系BFS
	source：源人名
	target：目标人名
	返回 搜索路径
	'''
	checked_person_list = []
	uncheck_person_list = []
	father_person_list = []
	relation_path = []
	source_person = []
	target_person = []
	# 找到 起始人物

	for person in global_person_list:
		if person.name == source or person.id == source:
			source_person.append(person)
		if person.name == target or person.id == target:
			target_person.append(person)

	if len(source_person) > 1:
		s = " ".join(["{}:{}".format(x.name, x.id) for x in source_person])
		print(s)
		return
	elif len(source_person) == 0:
		print("网络图中 没有{}".format(source))
		return
	else:
		source_person = source_person[0]
	if len(target_person) > 1:
		t = " ".join(["{}:{}".format(x.name, x.id) for x in target_person])
		print(t)
		return
	elif len(target_person) == 0:
		print("网络图中 没有{}".format(target))
		return
	else:
		target_person = target_person[0]

	uncheck_person_list.append(source_person)  # 将 起始人物 添加到 待检查列表
	relation_path.append(source_person.relation_with(source_person.name))  # 保存 已检查人物的关系
	father_person_list.append(source_person)  # 保存 已检查人物的父节点

	while(uncheck_person_list): # 待检查列表非空
		cur = uncheck_person_list[0]
		result = check_person(cur, target_person, checked_person_list, uncheck_person_list, father_person_list, relation_path)
		if result:
			break

	# checked_person_list 的 最后一个人 就是 搜索目标
	father_person_list = father_person_list[:len(checked_person_list)]
	relation_path = relation_path[:len(checked_person_list)]


	# for i in range(len(checked_person_list)):
	# 	print("{} - {} - {}".format(checked_person_list[i], father_person_list[i], relation_path[i]))
	# print(len(checked_person_list))
	# print(checked_person_list)
	# print(len(father_person_list))
	# print(father_person_list)
	# print(len(relation_path))
	# print(relation_path)

	
	ret = []  # 保存返回结果
	name = target_person

	# 回溯 路径
	while name != source_person:
		t = checked_person_list.index(name)
		# print("{} - {}- {}".format(father_person_list[t], relation_path[t], name))
		ret.append("{} - {} - {}".format(father_person_list[t].name, relation_path[t], name.name))
		t = checked_person_list.index(father_person_list[t])
		name = checked_person_list[t]

	# 反向输出，结果更直观
	ret.reverse()
	return ret
		
def Search(database, source, target):
	init(database)
	print("Searching ...")
	result = BFSsearch(source, target)
	if result is not None:  # 搜索人物有重名
		for i in result:
			print(i)


if __name__ == '__main__':
	'''
	运行说明，前三步只需运行一遍。后面即可进行搜索。
	relation_file 这里没有用到

	1. download_data()			#爬取数据，需要制定一个start_url，默认为鲁迅先生。爬取的人物数据默认保存在crawled_person_file中。为方便起见，关系数据单独拎出来一份，保存在crawled_relation_file中
	2. clean_data(crawled_person_file, cleaned_person_file)  # 清洗人物数据
	3. clean_relation_data(cleaned_person_file, crawled_relation_file, cleaned_relation_file)  # 清洗关系数据
	4. Search('鲁迅', '钱玄同')
	'''

	# download_data(r'https://baike.baidu.com/item/%E6%9B%B9%E6%93%8D/6772')
	# clean_data(crawled_person_file, cleaned_person_file)
	# clean_relation_data(cleaned_person_file, crawled_relation_file, cleaned_relation_file)
	Search('cleaned_person_file_鲁迅.txt', '鲁迅', '杨幂')
