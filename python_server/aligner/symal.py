import subprocess

class SymalWrapper(object):
    def __init__(self, symal_cmd):
        self.cmd = symal_cmd.split()

    def symmetrize(self, source_txt, target_txt, s2t_align, t2s_align):
        s_len = len(source_txt.split())
        t_len = len(target_txt.split())
        assert s_len == len(t2s_align)
        assert t_len == len(s2t_align)
        #s2t_align = " ".join([str(a+offset) for j,a in s2t_align])
        #t2s_align = " ".join([str(a+offset) for i,a in t2s_align])
        s2t_align = " ".join(map(str, s2t_align))
        t2s_align = " ".join(map(str, t2s_align))
        s = u"1\n%d %s  # %s\n%d %s  # %s\n" %(t_len, target_txt, t2s_align,
                                              s_len, source_txt, s2t_align)
        print "Input to symal: ", s.strip()
        proc = subprocess.Popen(self.cmd, stdin=subprocess.PIPE,
                                          stdout=subprocess.PIPE,
                                          stderr=subprocess.PIPE)
        result, err = proc.communicate(s.encode("utf-8"))
        print "Result from symal: ", repr(result)
        if not result.strip():
            return []
        result = result.split()
        result = [map(int, a.split('-')) for a in result]
        print "Processed: ", repr(result)
        return result
        #return result.decode("utf-8").rstrip()
