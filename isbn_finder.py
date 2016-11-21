import random
import sys
import threading
import time
import urllib

import bottlenose
import bs4

import multiprocessing

AWSAccessKeyId = "AKIAIMKJHSGQA6ASXMPQ"
AssociateTag = "seangrahamaws-20"
Signature = "RZDnfx964m4maCWSOvWCnPERW+NExH5RwAfpb9vI"

BOOK_TITLE_PADDING = 70
ISBN_PADDING = 15
DELAY = 10

class Book(object):
    def __init__(self, title, isbn, salesrank):
        self.title = title
        self.isbn = isbn
        self.salesrank = salesrank
    
    def __str__(self):
        return "%s %s %s" %(self.title.ljust(BOOK_TITLE_PADDING),
                            self.isbn.ljust(ISBN_PADDING),
                            self.salesrank)

class MyThread(threading.Thread):
    shared_lock = threading.Lock()

    def __init__(self, threadID, name, list_of_books):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name
        self.shared_list_of_books = list_of_books

    def run(self):
        book = amazon_api_call_by_isbn(self.name)

        with self.shared_lock:
            self.shared_list_of_books.append(book)

def error_handler(error):
    exception = error['exception']
    
    if isinstance(exception, urllib.request.HTTPError) and exception.code == 503:
        time.sleep(random.expovariate(0.1))
        return True

def amazon_api_call_by_isbn(isbn):
    amazon = bottlenose.Amazon(AWSAccessKeyId, 
                                    Signature, 
                                    AssociateTag, 
                                    ErrorHandler=error_handler)
    xmlResponse = amazon.ItemSearch(Keywords=isbn, 
                                        SearchIndex="All", 
                                        IdType="ISBN", 
                                        ResponseGroup="Large")
    parsedXML = bs4.BeautifulSoup(xmlResponse, "xml")
        
    title = parsedXML.Title.get_text()
    asin = parsedXML.ASIN.get_text()

    if parsedXML.SalesRank == None:
        salesRank = None
    else:
        salesRank = int(parsedXML.SalesRank.get_text())

    return Book(title, asin, salesRank)

def sequential_isbn_finder(passed_isbn_list):
    list_of_books = []
    for isbn in passed_isbn_list:
        list_of_books.append(amazon_api_call_by_isbn(isbn))
        
    return list_of_books

def order_books_by_rank(book_list):
    book_list.sort(key=lambda book: (book.salesrank is None, book.salesrank))

    return book_list

def print_book_list(book_list):
    print("%s %s %s" % ("Book title".ljust(BOOK_TITLE_PADDING), 
                        "isbn".ljust(ISBN_PADDING), 
                        "rank"))

    for book in book_list:
        print(book)

def threaded_isbn_finder(passed_isbn_list):
    threads = []
    threaded_books = []

    for i in range(len(passed_isbn_list)):
        threads.append(MyThread(i, passed_isbn_list[i], threaded_books))
        threads[i].start()

    for thread in threads:
        thread.join()

    return threaded_books

def parallel_isbn_finder(passed_isbn_list):
    jobs = []

    shared_queue = multiprocessing.Queue()

    for isbn in passed_isbn_list:
        process = multiprocessing.Process(target = process_worker, args=(isbn, shared_queue))
        jobs.append(process)
        process.start()

    for process in jobs:
        process.join()

    book_list = list(map((lambda x: shared_queue.get()), passed_isbn_list))

    return book_list

def process_worker(isbn, shared_queue):
    book = amazon_api_call_by_isbn(isbn)

    shared_queue.put(book)

def sleep_delay():
    print("Sleeping for " + str(DELAY) + " seconds because amazon or my internet does not like so many calls in a row.\n")
    time.sleep(DELAY)

def print_results(book_list, start_time):
    print_book_list(book_list)
    print("\n________________ %s seconds ________________\n" % (time.time() - start_time))

def time_run_of_isbn_finder(passed_isbn_list, description, create_book_list_function):
    start_time = time.time()
    print(description)
    book_list = order_books_by_rank(create_book_list_function(passed_isbn_list))
    print_results(book_list, start_time)

if __name__ == '__main__':

    filename = sys.argv[1]

    isbn_list = open(filename).read().splitlines()

    time_run_of_isbn_finder(isbn_list, "Sequential api calls:\n", sequential_isbn_finder)

    sleep_delay()

    time_run_of_isbn_finder(isbn_list, "Traditional threading api calls:\n", threaded_isbn_finder)

    sleep_delay()

    time_run_of_isbn_finder(isbn_list, "Parallel using multiprocessing api calls:\n", parallel_isbn_finder)
