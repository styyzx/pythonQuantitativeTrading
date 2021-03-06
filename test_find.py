# coding:utf-8

import tushare as ts
import pymysql
import numpy as np
import datetime
import time
import pandas as pd
import sys
# 通达信接口
from pytdx.hq import TdxHq_API
api = TdxHq_API()

# tushare接口
ts.set_token('b072d98ad9c6b41cb816bee74cc36646a0a0fbd5fb404b5c58b04e70')
pro = ts.pro_api()

b_con = 0
if api.connect('119.147.212.81', 7709):
    b_con = 1

# 数据库连接
db = pymysql.connect(host='localhost', port=3306, user='root', passwd='123456', db='tushare', charset='utf8mb4')

import datetime
import chinese_calendar

def getYesterday(today):
    oneday = datetime.timedelta(days=1)
    yesterday = today - oneday
    return yesterday

def getLastWorkDay(today):
    yesterday = getYesterday(today)
    while chinese_calendar.is_workday(yesterday) == False:
        yesterday = getYesterday(yesterday)
    return yesterday



def execute_sql_str(sql_str):
    # 使用cursor()方法获取操作游标
    cursor_temp = db.cursor()
    # sql = "delete from stock_daily_find"
    try:
        # 执行sql语句
        cursor_temp.execute(sql_str)
        # 提交到数据库执行
        db.commit()
    except Exception as e:
        print(e)
        # 如果发生错误则回滚
        db.rollback()
    # 关闭游标
    cursor_temp.close()


def execute_sql_file(sql_path):
    cursor_temp = db.cursor()
    with open(sql_path, 'r+') as f:
        # every sql job last line marked;
        sql_list = f.read().split(';')[:-1]
        sql_list = [x.replace('\n', ' ') if '\n' in x else x for x in sql_list]
    for sql_item in sql_list:
        print(sql_item)
        try:
            cursor_temp.execute(sql)
            # 提交到数据库执行
            db.commit()
        except Exception as e:
            print(e)
            # 如果发生错误则回滚
            db.rollback()

    # 关闭游标
    cursor_temp.close()


# execute_sql_file('sql_file/daily_info.sql')

daily_tab_name = 'stock_daily_' + time.strftime("%Y_%m_%d", time.localtime())
daily_sql = 'CREATE TABLE `' + daily_tab_name + '''` (
  `ts_code` varchar(10) NOT NULL COMMENT '股票代码',
  `trade_date` date NOT NULL COMMENT '交易日期',
  `open` double DEFAULT NULL COMMENT '开盘价',
  `high` double DEFAULT NULL COMMENT '最高价',
  `low` double DEFAULT NULL COMMENT '最低价',
  `close` double DEFAULT NULL COMMENT '收盘价',
  `cur_pct_chg` double DEFAULT NULL COMMENT 'jrzf',
  `pre_close` double DEFAULT NULL COMMENT '昨日收盘价',
  `change` double DEFAULT NULL COMMENT '涨跌额',
  `pct_chg` double DEFAULT NULL COMMENT '涨跌幅',
  `vol` double DEFAULT NULL COMMENT '成交量 （手）',
  `amount` double DEFAULT NULL COMMENT '成交额 （千元）',
  `turnover_rate` double DEFAULT NULL COMMENT '换手率',
  `volume_ratio` double DEFAULT NULL COMMENT '量比',
  `vol_925` double DEFAULT NULL COMMENT '9.25val',
  `vol_925_ratio` double DEFAULT NULL COMMENT '量比2',
  UNIQUE KEY `ts_code_date` (`ts_code`,`trade_date`) USING BTREE COMMENT '以股票代码和日期作为主键',
  KEY `ts_code` (`ts_code`) USING BTREE,
  KEY `trade_date` (`trade_date`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 ROW_FORMAT=DYNAMIC;'''

execute_sql_str(daily_sql)

# 查询当前所有正常上市交易的股票列表
# data = pro.stock_basic(exchange='', list_status='L',
#                        fields='ts_code,symbol,name,area,industry,fullname,enname,market,exchange,curr_type,list_status,list_date,delist_date,is_hs')

# dataset = np.array(data)
# stock_list = dataset.tolist()
#print(stock_list)

# sql = "select cal_date from trade_cal where cal_date ='" + str(sys.argv[1]) + "' and is_open=1 order by cal_date"
# sql = "select cal_date from trade_cal where cal_date ='" + str('20211112') + "' and is_open=1 order by cal_date"

# print("stock_list len= ", stock_list.__len__())

# for each in stock_list:
# print(datetime.datetime.strftime('20211112', "%Y%m%d"))

today = datetime.date.today()
data = pro.daily(trade_date=getLastWorkDay(today).strftime("%Y%m%d"))
#data = pro.daily(trade_date='20211119')
cursor = db.cursor()
datalist = np.array(data).tolist()

insert_sql = "replace into " + daily_tab_name + "( ts_code, trade_date, `open`, high, low, `close`, pre_close, `change`, " \
                                        "pct_chg, vol, amount,vol_925,vol_925_ratio,cur_pct_chg) values ( %s,%s,%s,%s," \
                                        "%s,%s,%s,%s,%s,%s,%s,%s,%s,%s ) "

print(datalist.__len__())
# info = api.get_security_quotes( (0, 300473))
# print(info)

for data in datalist:
    if len(data) < 6 or float(data[2]) == 0:
        continue
    if (float(data[8]) > 9):
        # print(data)
        stock_code = data[0][0:6]
        parket_code = 1 if data[0][7:9] == 'SH' else 0
        print(parket_code, stock_code)
        if data[0].__len__() < 8 or data[0][0] == '3' or data[0][0] == '8' or data[0][:3] == '688':
            continue
        info = api.get_security_quotes((parket_code, stock_code))
        if info is None:
            print(parket_code, stock_code)
            continue
        data.append(str(float(info[0]['reversed_bytes3']) ))
        vol925_ratio = float(info[0]['reversed_bytes3']) / ( float(data[10]) * 10 )
        data.append(str( vol925_ratio*100 ))
        cur_pct_chg = (float(info[0]['price']) - float(info[0]['last_close'])) / ( float(info[0]['last_close']) )
        data.append(str( cur_pct_chg*100 ))
        #data.append(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
        # tdx_data = []
        # tdx_data.append(info[0]['code'])
        try:
            # 执行sql语句
            cursor.execute(insert_sql, data)
            # cursor.execute(sql2, tdx_data)
            # 提交到数据库执行
            db.commit()
        except Exception as e:
            print(e)
            # 如果发生错误则回滚
            db.rollback()
cursor.close()


def execute_query(sql_str):
    temp_cursor = db.cursor()
    temp_cursor.execute(sql_str)
    print("查询到行数:", temp_cursor.rowcount)

    for each in temp_cursor.fetchall():
        print(each)
    temp_cursor.close()


sql = "select ts_code,cur_pct_chg,vol_925,vol_925_ratio from " + daily_tab_name + " where vol_925_ratio > 5 order by " \
      "vol_925_ratio desc "
execute_query(sql)


api.disconnect()

