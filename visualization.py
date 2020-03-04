import os
import copy
import networkx as nx
import matplotlib.pyplot as plt


global_url_list = []  # 全局url
global_exists_url_list = []  # 全局已爬url
global_person_list = []  # 全局 person对象 列表
global_person_dict = {}  # 全局 person对象 词典。 {name: person}

crawled_person_file = 'persons.txt'  # 爬取的人物数据文件名
crawled_relation_file = 'relations.txt'  # 关系数据文件名
cleaned_person_file = 'cleaned_person_file.txt'  # 清洗后的人物数据文件
cleaned_relation_file = 'cleaned_relation_file.txt'  # 清洗后的关系数据文件

PERSON_NUM_TO_CRAWL = 50000  # 爬取的人物上限 

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
				print(name)
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

def main():
	init(cleaned_person_file)
	relations = []
	labels = {}
	edge_labels = {}
	with open(cleaned_relation_file, 'r', encoding='utf-8') as f:
		for line in f:
			line = line.split("'")
			source = line[1]
			target = line[3]
			rela = line[7]
			print(source, target, rela)
			relations.append((source, target, {'': rela}))
			labels[source] = global_person_dict[source].name
			labels[target] = global_person_dict[target].name
			edge_labels[(source, target)] = rela

	G = nx.Graph() # 创建有向图
	G.add_edges_from(relations)
	pos = nx.kamada_kawai_layout(G)  # 环形布局

	nx.draw_networkx_nodes(G, pos=pos, node_size=300, node_color='blue', node_shape='.', alpha=1, edge_color='red', width=3)
	nx.draw_networkx_labels(G, pos=pos, labels=labels, font_size=10, font_family='YouYuan', font_weight='bold')
	nx.draw_networkx_edges(G, pos=pos, alpha=1, edge_color='red', width=2, style='solid')

	plt.show()

if __name__ == '__main__':
	main()
