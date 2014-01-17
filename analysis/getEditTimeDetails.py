#!/usr/bin/env python
import sys,os,MySQLdb
import xmlrpclib,HTMLParser,cgi
from matecat import *

def getTime(DB,who,job=None):
    c = DB.cursor()
    q  = 'select e.* from '
    q += 'log_event_header e '
    q += 'INNER JOIN jobs j on j.id = e.job_id '
    if job:
        q += 'where j.id_translator = %s and j.id = %s order by e.job_id,e.time'
        c.execute(q,(who,job))
    else:
        q += 'where j.id_translator = %s order by e.time'
        c.execute(q,(who))
        pass
    total = 0
    ljob  = 0
    ltime = 0
    for x in c:
        # print x
        t = int(x['time'])/1000
        if x['job_id'] != ljob:
            ljob = x['job_id']
        elif ltime and t - ltime < 600:
            total += t - ltime
            pass
        ltime = t
        pass
    return total

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-dbase', help='name of mysql database',default="casmaccept_hytra_II")
    parser.add_argument('-user', help='mysql user name',default='readonly')
    parser.add_argument('-passwd', help='mysql password',default='ro-password')
    parser.add_argument('-split', help='split segments into control and test',action="store_true")
    parser.add_argument('who',help='project name')

    args = parser.parse_args(sys.argv[1:])

    DB = MateCat(args.dbase,args.user,args.passwd)
    who = args.who
    P  = Project(DB,who)
    et0 = 0
    et1 = 0
    wc0 = 0
    wc1 = 0
    ctr = 0
    if (args.split):
        dat0 = open("%s.progress.0"%who,'w')
        dat1 = open("%s.progress.1"%who,'w')
    else:
        dat1 = sys.stdout
        pass
    

    for j in P.jobs:
        jet = getTime(DB,who,j.id)
        # print j.id, jet, hms(jet)
        for f in j.files:
            for s in f.segments:
                if len(s.trans) == 0: continue
                td  = s.getEditTime(DB)/1000
                if td == 0: continue
                ctr += 1
                if args.split and ctr % 10 == 0:
                    wc0 += s.rwc
                    et0 += td
                    out = dat0
                    wc = wc0
                    et = et0
                else:
                    wc1 += s.rwc
                    et1 += td
                    out = dat1
                    wc = wc1
                    et = et1
                    pass
                d = ""
                if s.timestamp: d = time.strftime("%d.%m:%H.%M",s.timestamp)
                print >>out, \
                    "%6d %s [%4d:%4d] %3d sec. %3d %6d wrds %4.2f wrds/hr. %s"\
                    %(et,hms(et),f.id,s.id,td,s.rwc,wc,wc/(float(et)/3600),d)
                pass
            pass
        pass
    
    
