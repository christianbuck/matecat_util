#!/usr/bin/env python
import sys,os,MySQLdb,time
import xmlrpclib,HTMLParser,cgi

def hms(secs):
    s = secs%60
    secs /= 60
    m = secs%60
    secs /= 60
    h = secs
    return "%d:%02d:%02d"%(h,m,s)

class MateCat(object):
    def __init__(self,dbase,user,passwd):
        self.db = MySQLdb.connect(passwd=passwd,user=user,db=dbase)
        pass
    def cursor(self):
        return self.db.cursor(MySQLdb.cursors.DictCursor)
    pass

class Segment(object):
    def __init__(self,DB,fid,S):
        self.fid   = fid
        self.id    = S['id']
        self.seqno = S['internal_id']
        self.text  = S['segment']
        self.rwc   = S['raw_word_count']
        self.timestamp = None
        c = DB.cursor()
        c.execute("""SELECT status,translation FROM segment_translations where id_segment = %s""",(self.id))
        self.trans = [t for t in c]
        pass
    def delete(self,DB):
        c = DB.cursor()
        c.execute("""DELETE FROM segment_translations where id_segment = %s""",(self.id))
        c.execute("""DELETE FROM segments where id = %s""",(self.id))
        pass
    def getEditTime(self,DB,maxidle=5):
        key = "segment-%d"%self.id
        q   = "SELECT file_id,time,element_id,type "
        # q   = "SELECT * "
        q  += "from log_event_header WHERE type != 'gaze' AND type != 'fixation' "
        q  += "AND file_id = %%s and substr(element_id,1,%d) = %%s "%len(key)
        q  += "ORDER BY time"
        c = DB.cursor()
        c.execute(q,(self.fid,key))
        lasttime = 0
        ret = 0
        for x in c:
            if not self.timestamp:
                self.timestamp = time.localtime(int(x['time'])/1000)
            if x['type'] == 'segmentOpened':
                lasttime = int(x['time'])
            else:
                d = int(x['time']) - lasttime
                if lasttime and d < maxidle*60000: 
                    ret += d
                    # print d,x
                    pass
                if x['type'] != 'segmentClosed':
                    lasttime = int(x['time'])
                else:
                    lasttime = 0
                    pass
                pass
            pass
        return ret
    pass

class File(object):
    def __init__(self,DB,F):
        self.id = F['id_file']
        self.segments = []
        c = DB.cursor()
        c.execute("""SELECT * from segments where id_file = %s order by id""",(self.id))
        for s in c:
            self.segments.append(Segment(DB,self.id,s))
            pass
        pass

    def delete(self,DB):
        for s in self.segments: s.delete(DB)
        c = DB.cursor()
        c.execute("""DELETE from files WHERE id = %s""",(self.id))
        c.execute("""DELETE from files_job WHERE id_file = %s""",(self.id))
        pass
    def getEditTime(self,DB,maxidle=5):
        return sum([s.getEditTime(DB,maxidle) 
                    for s in self.segments])
    def getCompletionRatio(self):
        total = len(self.segments)
        done  = len([s for s in self.segments 
                     if len(s.trans) and s.trans[0][0] != 'NEW'])
        return (done,total)
    pass
        
class Job(object):
    def __init__(self,DB,F):
        self.id         = F['id']
        self.passwd     = F['password']
        self.web_id     = "%d-%s"%(self.id,self.passwd)
        self.source     = F['source'][:2]
        self.target     = F['target'][:2]
        self.mt_engine  = F['id_mt_engine']
        self.translator = F['id_translator']
        c = DB.cursor()
        c.execute("""SELECT id_file from files_job where id_job = %s order by id_file""",(self.id))
        self.files      = [File(DB,f) for f in c]
        pass
    
    def delete(self,DB):
        for f in self.files: f.delete(DB)
        c = DB.db.cursor()
        c.execute("""DELETE FROM jobs WHERE id = %s""",(self.id))
        pass

    def assign(self,DB,translator,password):
        c = DB.db.cursor()
        c.execute("""UPDATE jobs SET id_translator = %s,password = %s WHERE id = %s""",
                  ((translator,password,self.id)))
        self.translator = translator
        pass
    pass



class Project(object):
    def __init__(self,DB,name):
        self.name = name
        self.jobs = []
        self.id   = None
        c = DB.cursor()
        c.execute("""SELECT id from projects where name = %s order by id""",(name))
        for p in c:
            J = DB.cursor()
            J.execute("""SELECT * from jobs where id_project = %s order by id""",(p['id']))
            for j in J:
                self.jobs.append(Job(DB,j))
                pass
            pass
        return

    def assign(self,DB,translator):
        """Assign project to a translator"""
        passwd = self.jobs[0].passwd
        for j in self.jobs:
            j.assign(DB,translator,passwd)
            pass
        return

    def consolidate(self,DB):
        c = DB.cursor()
        c.execute("""SELECT id from projects where name = %s order by id""",(self.name))
        for p in c:
            if self.id == None: 
                self.id = p['id']
            elif self.id != p['id']:
                x = DB.cursor()
                x.execute("DELETE from projects where id = %s",(p['id']))
                pass
            pass
        for j in self.jobs:
            x = DB.cursor()
            x.execute("UPDATE jobs SET id_project = %s where id = %s",(self.id,j.id))
            pass
        return
    pass

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-dbase', help='name of mysql database',default="casmaccept_hytra_II")
    parser.add_argument('-user', help='mysql user name',default='casmaccept')
    parser.add_argument('-passwd', help='mysql password',default='geneva')
    args = parser.parse_args(sys.argv[1:])

    DB = MateCat(args.dbase,args.user,args.passwd)

    c = DB.cursor()
    c.execute('select * from jobs')
    x = c.fetchall()
    for y in x:
        print y
        pass
    sys.exit(0)

    # P  = Project(DB,'forum')
    # print P.name
    # for j in P.jobs:
    #     if j.mt_engine: 
    #         print "JOB http://uli.casmacat.eu/translate/%s/%s-%s/%s"\
    #             %(P.name,j.source,j.target,j.web_id)
    #         for f in j.files:
    #             print f.id, f.getCompletionRatio(),
    #             print hms(f.getEditTime(DB,5)/1000)
    #             pass
    #         pass
    #     else:
    #         # j.delete(DB)
    #         pass
    #     pass
    # pass

