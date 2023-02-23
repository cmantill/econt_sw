import sqlite3
import os

# #create database
# def create_database(database_name = 'Econt_database', table_name = 'Econt_table'):
#     conn = sqlite3.connect(f"{database_name}.db")
#     # #create curse
#     c = conn.cursor()
#
#     # create table
#     c.execute(f"""CREATE TABLE  {table_name}(
#     Output_dir DATATYPE,
#     Chip DATATYPE,
#     Date_time_end DATATYPE
#
#     )""")
#     conn.close()
def create_database(database_name = 'Econt_database', table_name = 'Econt_table'):
    conn = sqlite3.connect(f"{database_name}.db")
    # #create curse
    c = conn.cursor()

    # create table
    c.execute(f"""CREATE TABLE  {table_name}(

    Date_time_end DATATYPE,
    Output_dir DATATYPE,
    Power DATATYPE,
    over_all_test DATATYPE,
    RW_test DATATYPE,
    Pll_test DATATYPE,
    Phase_width_test DATATYPE,
    IO_scan_width_tresold DATATYPE,
    IO_scan_max_width_tresold DATATYPE,
    IO_scan_second_width_tresold DATATYPE,
    delay_scan_max_width_tresold DATATYPE,
    delay_scan_second_width_test DATATYPE,
    test_end DATATYPE

    )""")
    conn.close()

# load whole database to  XXX:
def load_database( database_name='Econt_database', table_name = 'Econt_table'):
    conn = sqlite3.connect(f'{database_name}.db')
    c = conn.cursor()
    c.execute(f"SELECT  rowid, * FROM {table_name}")
    return c.fetchall()

# show in rows for each entry
def show_all_plan(database_name='Econt_database', table_name = 'Econt_table'):
    conn = sqlite3.connect(f'{database_name}.db')
    c = conn.cursor()
    c.execute(f"SELECT  rowid, * FROM {table_name}")
    data = c.fetchall()
    for item in data:
        print(item)

#show with header more artistic
def show_all(database_name='Econt_database', table_name = 'Econt_table'):
    conn = sqlite3.connect(f'{database_name}.db')
    c = conn.cursor()
    c.execute(f"SELECT  rowid, * FROM {table_name}")
    data = c.fetchall()
    print("--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------")
    print( 'rowid',' |     ','start D/T','     |     ' ,'End D/T','   |    ', 'Data Directory','  |  ','Chip','  | ','Power',' | ','All test','|','R/W test','|','PLL test','|',
     'Phase scan Width Test','|','IO scan Width test','  |')
    print("--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------")
    for item in data:
        print(item[0],"    ",item[1],"   ",item[2],"  ", item[3],"    ",item[4],"   ",item[5],"    ",item[6],"    ",item[7],"    ",
        item[8],"             ", item[9] ,"                ", item[10],'   |  ')
    print("--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------")
    conn.commit()
    conn.close()

# add new row
def add_one_row(item1,item2,item3,item4,item5,item6,item7,item8, item9, database_name='Econt_database', table_name='Econt_table'):
    conn = sqlite3.connect(f'{database_name}.db')
    c = conn.cursor()
    c.execute(f"""INSERT INTO {table_name} VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",(item0,item1,item2,item3,item4,item5,item6,item7,item8,item9,item10,item11,item12))
    conn.commit()
    conn.close()

# update one value in row
def update_one_in_row(where, value, row, database_name='Econt_database', table_name='Econt_table'):
    conn = sqlite3.connect(f'{database_name}.db')
    c = conn.cursor()
    c.execute(f""" UPDATE {table_name} SET '{where}' = '{value}' WHERE rowid = {row} """)
    conn.commit()
    conn.close()

# delete a row
# pass row as string
def delete_one_row(row, database_name='Econt_database', table_name='Econt_table'):
    conn = sqlite3.connect(f'{database_name}.db')
    c = conn.cursor()
    c.execute(f"""DELETE from {table_name} WHERE rowid = {row} """)
    conn.commit()
    conn.close()

#add many record may rows (list of string)
def add_many_column(list, database_name='Econt_database', table_name='Econt_table'):
    conn = sqlite3.connect(f'{database_name}.db')
    c = conn.cursor()
    c.executemany(f"""INSERT INTO {table_name} VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",(list))
    conn.commit()
    conn.close()
# #add many record may rows (list of string)
# def add_many_column(list, database_name='Econt_database', table_name='Econt_table'):
#     conn = sqlite3.connect(f'{database_name}.db')
#     c = conn.cursor()
#     c.executemany(f"""INSERT INTO {table_name} VALUES (?,?,?)""",(list))
#     conn.commit()
#     conn.close()


# find in data database

def lookup(what, value, database_name='Econt_database', table_name='Econt_table'):
    conn = sqlite3.connect(f'{database_name}.db')
    c = conn.cursor()
    c.execute(f""" SELECT rowid, * from {table_name} WHERE {what} = '{value}' """)
    items = c.fetchall()
    for item in items:
        print(item)
    conn.commit()
    conn.close()


# conn = sqlite3.connect(":memory:")
# if os.path.exists("Econt_database.db1") == False:
#     conn = sqlite3.connect("Econt_database1.db")
#     # #create curse
#     c = conn.cursor()
#
#     # create table
#     c.execute("""CREATE TABLE  Econt_table(
#     first_name DATATYPE,
#     last_name DATATYPE
#     )""")
#     conn.close()

# if os.path.exists("Asic_Test.db") == False:
#     create_database()
# show_all()
#THIS ONLY HAVE 5 TYPE OF DATATYPE:
#NULL
#INTERGER
#REAL
#TXT
#BLO
# conn = sqlite3.connect("Asic_Test.db")
# # #create curse
# c = conn.cursor()
#
# # to write into table
# # c.execute(" INSERT INTO Econt_table VALUES ('Lila', 'Bam') ")
#
# # to read from esisting table
# # c.execute("SELECT * FROM ECON_T WHERE first_name LIKE 'Li%' ")
# # c.execute("SELECT * FROM ECON_T WHERE first_name = 'Lila' ")
# c.execute("SELECT rowid, * FROM ECON_T")
# # # c.fechone() # first entry
# # # c.fetchmany(2) #
# # # print(c.fetchall()) # all
# data = c.fetchall()
# print("Name","   ","Last Name")
# print("------","   ","-----------")
# for item in data:
#     print(item[0],"   " ,item[1])
# print("commamd excutated success")

#update data base
# c.execute("""UPDATE ECON_T SET first_name='YYY' WHERE first_name = 'XXX'
# """)
# c.execute("""UPDATE ECON_T SET first_name = 'hari'
# WHERE rowid=16
# """)

# delete record
# c.execute("""DELETE from ECON_T WHERE first_name='XXX' """)

# ordring
# c.execute("""SELECT rowid, * FROM ECON_T ORDER BY first_name DSC """)

# commit our command
# conn.commit()
# # c.execute("SELECT rowid, * FROM ECON_T")
# # print(c.fetchall())
# #close commection
# conn.close()

# query database
