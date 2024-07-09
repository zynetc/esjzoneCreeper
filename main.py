import yaml
import requests
import os
import time
from selenium import webdriver
from bs4 import BeautifulSoup
from ebooklib import epub
import pickle
#爬虫对象
ss=requests.session()


def check_login(relogin=False):
    print('正在登陆')
    while True:
        #如果cookies存在-->尝试演奏登录
        if os.path.exists('cookies.yaml') and relogin==False:
            #读取文件
            with open('cookies.yaml','r')as f:
                cookies=yaml.load(f.read(),Loader=yaml.FullLoader)
            #创建cookies对象
            c = requests.cookies.RequestsCookieJar()
            #加载cookies数据
            for cookie in cookies:
                c.set(cookie['name'],cookie['value'],path=cookie['path'],domain=cookie['domain'])
            ss.cookies.update(c)
            #验证登录
            responce=ss.get('https://www.esjzone.me/my/profile').text
            if 'login' in responce:
                print('登陆失败，请重新登录')
                relogin=True
            else:
                print('验证登录成功')
                break
        
        #重新登录
        if os.path.exists('cookies.yaml')==False or relogin==True:
            #创建浏览器驱动程序
            opentions=webdriver.ChromeOptions()
            opentions.binary_location='chrome-win64/chrome.exe'
            opentions.add_experimental_option('excludeSwitches', ['enable-logging'])#禁止打印日志
            opentions.add_experimental_option('excludeSwitches', ['enable-automation'])#实现了规避监测
            opentions.add_argument('--log-level=1')
            opentions.add_argument('--ignore-ssl-error')
            browser=webdriver.Chrome(options=opentions)
            browser.get('https://www.esjzone.me/my/login')
            while True:
                if 'profile' in browser.current_url:
                    break
                time.sleep(0.1)
            #保存cookies信息
            cookies=browser.get_cookies()
            browser.close()
            browser.quit()
            with open('cookies.yaml','w')as f:
                yaml.dump(cookies,f)
            relogin=False


def get_info(url):
    #获取网页
    response=ss.get(url).text
    soup = BeautifulSoup(response, 'lxml')
    #获取基本信息
    detal=soup.find("div",class_='col-md-9 book-detail')
    #标题
    title=detal.find('h2').get_text()
    print('书名：{}\n地址：{}'.format(title,url))
    #基本信息
    info=''
    for t in detal.find_all('li',class_=''):
        info=info+t.get_text()+'\n'
    # 下载图片
    workpath='book/{}/chapter'.format(title)
    if not os.path.exists(workpath):#如果路径不存在
        os.makedirs(workpath)
    try:
        picurl=soup.find('div',class_='product-gallery text-center mb-3').find('a').get('href')
        pic = ss.get(picurl).content
    except:
        with open('chrome-win64/cover.jpg','rb')as f:
            pic=f.read()
    with open("book/{}/cover.jpg".format(title) ,mode = "wb") as f:
        f.write(pic) #图片内容写入文件
    #介绍
    description=soup.find('div',class_='description').get_text()
    with open("book/{}/info.txt".format(title),"w",encoding='utf-8') as f:
        f.write(info)
    with open("book/{}/description.txt".format(title),"w",encoding='utf-8') as f:
        f.write(description)
    #章节信息
    chapters={}
    chapterList=soup.find("div",id="chapterList")
    for t in chapterList.find_all('a'):
        chapters[t['data-title']]=t['href']
    return_data=[title,info,chapters,description]
    with open(f'book/{title}/data.bin','wb') as f:
        pickle.dump(return_data,f)
    return return_data

def download_story(book_data):
    num=len(book_data[2])
    index=0
    for chapter_name,url in book_data[2].items():
        #进度条
        print("{}/{}    |{}{}|{}%".format(index,num,"█"*int((50*index)/num)," "*int(50-(50*index)/num),int(100*index/num)),end='\r')


        # print(index,url)
        
        if os.path.exists(f"book/{book_data[0]}/chapter/{index}.txt"):
            index=index+1
            continue
        response=ss.get(url).text
        soup = BeautifulSoup(response, 'lxml')
        doct = soup.find('div',class_='forum-content mt-3')
        lines=doct.find_all('p')
        for line in lines:
            # print(line.text)
            with open('book/{}/chapter/{}.txt'.format(book_data[0],index),'a+',encoding='utf8') as f:
                f.write(line.text)
                f.write('\n')
        index=index+1
        time.sleep(1)
        

def save2ebup(book_data):
    # with open(f'book/{book_name}/data.bin','rb') as f:
    #     book_data=pickle.load(f)
    # 创建EPUB书籍对象
    book = epub.EpubBook()
    # 设置书籍的元数据
    book.set_identifier(book_data[0]) # 书籍的唯一标识符
    # 封面
    cover_image="book/{}/cover.jpg".format(book_data[0])
    book.set_cover(cover_image, open(cover_image, 'rb').read())
    book.set_title(book_data[0]) # 书籍的标题 
    book.set_language('zh') # 书籍的语言

    bookinfo=book_data[1].split('\n')
    author=''
    for t in bookinfo:
        if '作者' in t:
            author=t.split(':')[1]
            break

    book.add_author(author) # 书籍的作者  
    # 创建 CSS 样式
    css_text = '''  
    @namespace epub "http://www.idpf.org/2007/ops";    
    body {        font-family: "Times New Roman", Times, serif;    }    
    p {        text-indent: 2em; /* 设置段落首行缩进 */        margin-top: 0;        margin-bottom: 1em;    }    
    '''  
    # 创建一个 CSS 文件对象 
    style = epub.EpubItem(uid="style", file_name="style/style.css", media_type="text/css", content=css_text)  
    # 将 CSS 文件添加到 EPUB 书籍中
    book.add_item(style)
    # 创建前言页面
    c1 = epub.EpubHtml(title='前言', file_name='intro.xhtml', lang='zh')
    c1.content = f'<html><head></head><body><h1>{book_data[0]}</h1><p>{book_data[1]}<p>简介：{book_data[3]}</p></body></html>'  
    book.add_item(c1)
    # 初始化书脊  
    spine = ['nav', c1] 
    # 添加章节
    index=0
    for chapter_name in book_data[2].keys():
        # print(chapter_name)
        title = chapter_name
        content=''
        with open(f"book/{book_data[0]}/chapter/{index}.txt",encoding='utf-8') as f:
            lines=f.readlines()
        for line in lines:
            content=f"{content} <p> {line.strip()} </p>"
        # print(content)
        # #替换换行符
        # content=content.replace('\n','<br>')
        # 创建 EPUB 格式的章节
        epub_chapter = epub.EpubHtml(title=title, file_name=f'{index}.xhtml', lang='zh')  
        epub_chapter.content = f'<html><head><style type="text/css">{css_text}</style></head><body><h2>{title}</h2>{content}</body></html>'
        book.add_item(epub_chapter)
        spine.append(epub_chapter) 
        index=index+1
    # 设置书脊  
    book.spine = spine  
    # 创建目录列表，开始时包括前言链接 
    toc = [epub.Link('intro.xhtml', '前言', 'intro')] 
    # 对于每个章节，添加一个章节链接到目录列表中  
    index=0
    for chapter_name in book_data[2].keys(): 
        title = chapter_name
        # 创建章节的链接对象
        chapter_link = epub.Link(f'{index}.xhtml', title, f'{chapter_name}')  
        toc.append(chapter_link)
        index=index+1
    # 最后，将目录列表设置为书籍的 TOC    
    book.toc = tuple(toc)  
    # 添加必要的 EPUB 文件  
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())  
    # 保存 EPUB 文件 
    if not os.path.exists(f"out"):
        os.makedirs("out")
    epub_path = f'out/{book_data[0]}.epub'  
    epub.write_epub(epub_path, book, {})  
    print(f"EPUB 文件已创建: {epub_path}")  
    pass

def search(keyword):
    url=f"https://www.esjzone.me/tags/{keyword}/"
    response=ss.get(url).text
    soup = BeautifulSoup(response, 'lxml')
    resault=soup.find('div',class_='col-xl-9 col-lg-8 p-r-30')
    books=resault.find_all('div',class_='col-lg-3 col-md-4 col-sm-3 col-xs-6')
    # nextpage=resault.find()
    book_dict={}
    for t in books:
        book_dict[t.find('div',class_='card mb-30')['title']]="https://www.esjzone.me{}".format(t.find('a',class_='card-img-tiles')['href'])
    keys=list(book_dict.keys())

    for index in range(len(keys)):
        print(f"[{index}]  {keys[index]}")
    while True:
        get_index=input("请输入编号： (Q返回)")
        if get_index=='Q' or get_index=='q':
            return ''
        else:
            if get_index.isdigit():
                get_index=int(get_index)
                if get_index<=len(keys):
                    # print(get_index)
                    # print(book_dict[keys[get_index]])
                    return book_dict[keys[get_index]]
        print('\r 输入不合法')



def main():
    check_login()
    while True:
        choice=''
        url=''
        keyword=''
        os.system("cls")
        print('[1] 关键词')
        print('[2] 地址')
        print('[3] 重复上次')
        choice=input()
        if choice=='1':
            while True:
                keyword=''
                keyword=input('请输入关键字(Q退出)')
                if keyword=='q' or keyword=='Q':
                    break
                if keyword!="":
                    url=search(keyword)
                    break

        if choice=='2':
            while True:
                url=''
                url=input('请输入地址(Q退出)')
                print(url)
                if url=='q' or url=='Q':
                    url=''
                    break
                if 'detail' in url:
                    break
                else:
                    print('\r输入不合法')

        if choice=='3':
            while True:
                #读取配置信息
                book_name=''
                with open('_temp','r',encoding='utf-8')as f:
                    lines=f.readlines()
                    
                    history_data=lines[-1].strip().split('---')
                    book_name=history_data[0]
                    url3=history_data[1]
                    os.system("cls")
                    print("上次数据")
                    print(book_name)
                    print(url3)
                    print("----------------------------------------------------------------")
                    print('[1] 直接重试')
                    print('[2] 刷新数据')
                    print('[q] 返回')
                    choice3=''
                    choice3=input()
                    if choice3=='1':
                        with open(f'book/{book_name}/data.bin','rb') as f:
                            book_data=pickle.load(f)
                            break
                    if choice3=='2':
                        url=url3
                        break
                    if choice3=='q' or choice3=='Q':
                        break

        
        #建立任务
        if url != '':
            book_data=get_info(url)
            #保存临时文件
            with open("_temp","a+",encoding='utf-8')as f:
                f.write('\n'+book_data[0]+'---'+url)
        

        if 'book_data' in locals().keys(): 
            #开始下载
            download_story(book_data)
            save2ebup(book_data)



            


        






# url="https://www.esjzone.me/detail/1646200959.html"
# check_login()
# book_data=get_info(url)
# download_story(book_data)
# save2ebup(book_data[0])
# print(search('努力'))
main()