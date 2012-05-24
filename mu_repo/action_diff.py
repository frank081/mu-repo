'''
Created on 19/05/2012

@author: Fabio Zadrozny
'''
from mu_repo import thread_pool
from mu_repo.print_ import Print
import os.path
import shutil
import subprocess
from mu_repo.execute_git_command_in_thread import ExecuteGitCommandThread
from Queue import Queue
from mu_repo.rmtree import RmTree

#Erorr listeners may add themselves here (activated when errors happen in a worker thread).
on_errors_listeners = set()

#===================================================================================================
# NotifyErrorListeners
#===================================================================================================
def NotifyErrorListeners():
    import StringIO
    import traceback
    cstr = StringIO.StringIO()
    traceback.print_exc(file=cstr)
    error = cstr.getvalue()
    for listener in on_errors_listeners:
        listener(error)
    Print(error)


#===================================================================================================
# ExecuteGettingStdOutput
#===================================================================================================
def ExecuteGettingStdOutput(cmd, cwd):
    p = subprocess.Popen(
        cmd,
        cwd=cwd,
        #stderr=subprocess.STDOUT, # -- let stderr go to sys.stderr!
        stdout=subprocess.PIPE,
        stdin=subprocess.PIPE
    )

    stdout, _stderr = p.communicate()
    return stdout


#===================================================================================================
# CreateFromGit
#===================================================================================================
class CreateFromGit(object):

    __slots__ = ['_args']

    def __init__(self, *args):
        self._args = args

    def __call__(self):
        try:
            git, repo, original_repo, target_repo = self._args
            stdout = ExecuteGettingStdOutput(
                '%s show HEAD:%s' % (git, original_repo,), repo)

            try:
                if not os.path.isdir(target_repo):
                    with open(target_repo, 'wb') as f:
                        f.write(stdout)
            except:
                print 'Error writing to file: %s\n%s' % (target_repo, stdout,)
        except:
            NotifyErrorListeners()

#===================================================================================================
# Symlink
#===================================================================================================
class Symlink(object):

    __slots__ = ['_args']

    def __init__(self, *args):
        self._args = args

    def __call__(self):
        try:
            symlink, original, link = self._args
            symlink(
                original,
                link
            )
        except:
            NotifyErrorListeners()


#===================================================================================================
# StatusEntry
#===================================================================================================
class StatusEntry(object):

    __slots__ = ['filename', 'filename_from']

    def __init__(self, filename, filename_from):
        self.filename = filename
        self.filename_from = filename_from

    def __str__(self):
        return 'StatusEntry [%s, %s]' % (self.filename, self.filename_from)

    __repr__ = __str__

    def MakeDirs(self, temp_working, temp_repo, repo):
        dirname = os.path.dirname
        join = os.path.join
        basename = os.path.basename
        exists = os.path.exists
        makedirs = os.makedirs
        filename = self.filename

        #Make the directory structure in the working dir
        tdir = join(temp_working, repo, dirname(filename))
        if not exists(tdir):
            makedirs(tdir)

        #Make the directory structure in the repo dir
        fdir = join(temp_repo, repo, dirname(filename))
        if not exists(fdir):
            makedirs(fdir)

        #Current working dir original file and created link
        original = join(repo, filename)

        if filename != self.filename_from:
            filename += '  was  ' + basename(self.filename_from)

        link = join(temp_working, repo, filename)

        #Current repository original file and the target in the diff structure
        original_repo = self.filename_from
        target_repo = join(temp_repo, repo, filename)

        return original, link, original_repo, target_repo


#===================================================================================================
# ParsePorcelain
#===================================================================================================
def ParsePorcelain(porcelain_output):
    it = iter(porcelain_output.split('\0'))
    for entry in it:
        entry = entry.strip()
        if not entry:
            continue
        for i, c in enumerate(entry):
            if c == ' ':
                break
        st = entry[:i].strip()
        entry = entry[i:].strip()
        if not st:
            continue #Unmodified
        if 'R' in st:
            filename_from = next(it)
            yield StatusEntry(entry, filename_from)
        else:
            yield StatusEntry(entry, entry)


#===================================================================================================
# DoDiffOnRepoThread
#===================================================================================================
class DoDiffOnRepoThread(ExecuteGitCommandThread):


    def __init__(self, config, repo, symlink, temp_working, temp_repo):
        self.symlink = symlink
        self.temp_working = temp_working
        self.temp_repo = temp_repo
        args = 'status --porcelain -z'.split()

        ExecuteGitCommandThread.__init__(self, repo, args, config, output_queue=Queue(), put_raw_output=True)


    def run(self):
        try:
            ExecuteGitCommandThread.run(self, serial=False)
        except:
            NotifyErrorListeners()


    def _HandleOutput(self, msg, stdout):
        temp_working, temp_repo, repo = self.temp_working, self.temp_repo, self.repo
        for entry in ParsePorcelain(stdout):
            original, link, original_repo, target_repo = entry.MakeDirs(temp_working, temp_repo, repo)

            if not os.path.exists(original):
                with open(link, 'w') as f:
                    f.write('File: %s was removed in working dir.' % (original,))
            else:
                thread_pool.AddTask(
                    Symlink(self.symlink, original, link)
                )

            thread_pool.AddTask(
                CreateFromGit(self.config.git or 'git', self.repo, original_repo, target_repo)
            )





#===================================================================================================
# Run
#===================================================================================================
def Run(params):
    config = params.config
    git = config.git or 'git'

    join = os.path.join

    temp_dir_name = '.mu.diff.git.tmp'

    if os.path.exists(temp_dir_name):
        n = ''
        while n not in ('y', 'n'):
            n = raw_input(
                'Temporary dir for diff: %s already exists. Delete and continue (Y/n) or cancel (N/n)?' %
                (temp_dir_name,)
            ).strip().lower()
            if n == 'y':
                RmTree(temp_dir_name)
                break
            if n == 'n':
                Print('Canceling diff action.')
                return

    temp_working = join(temp_dir_name, 'WORKING')
    temp_repo = join(temp_dir_name, 'REPO')
    os.mkdir(temp_dir_name)
    os.mkdir(temp_working)
    os.mkdir(temp_repo)

    #===============================================================================================
    # Define symlink utility
    #===============================================================================================
    keep_files_synched = None
    try:
        if not hasattr(os, 'symlink'):
            import win32file
            #Note: not all users can do it...
            #http://stackoverflow.com/questions/2094663/determine-if-windows-process-has-privilege-to-create-symbolic-link
            #see: http://bugs.python.org/issue1578269
            #see: http://technet.microsoft.com/en-us/library/cc766301%28WS.10%29.aspx
            def symlink(src, target):
                win32file.CreateSymbolicLink(src, target, 1)
        else:
            symlink = os.symlink

        #Just check if it does indeed work... if it doesn't redefine and use our polling strategy.
        symlink(temp_working, join(temp_dir_name, 'lnk_test'))
    except:
        from mu_repo import keep_files_synched
        def symlink(src, target):
            if os.path.isdir(src):
                if os.path.exists(target):
                    os.rmdir(target)
                shutil.copytree(src, target)
                #This print is a TODO!
                Print('WARNING: TODO: Structure from: %s is copied (and not symlinked nor kept in sync).' % (target,))
            else:
                if os.path.exists(target):
                    if os.path.isdir(target):
                        RmTree(target)
                    else:
                        os.remove(target)
                shutil.copyfile(src, target)
                keep_files_synched.KeepInSync(src, target)

    try:
        #Note: we could use diff status --porcelain instead if we wanted to check untracked files.
        #cmd = [git] + 'diff --name-only -z'.split()
        threads = []
        for repo in config.repos:
            thread = DoDiffOnRepoThread(config, repo, symlink, temp_working, temp_repo)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        thread_pool.Join()

        winmerge_cmd = 'WinMergeU.exe /r /u /wr /dl WORKINGCOPY /dr HEAD'.split()
        cmd = winmerge_cmd + [temp_working, temp_repo]
        try:
            subprocess.call(cmd)
        except:
            Print('Error calling: %s' % (' '.join(cmd),))

        #If we've gono to the synching mode, make sure we had a last synchronization before
        #getting out of the diff.
        if keep_files_synched is not None:
            keep_files_synched.StopSyncs()
    finally:
        def onerror(*args):
            Print('Error removing temporary directory structure: %s' % (args,))
        RmTree(temp_dir_name, onerror=onerror)




