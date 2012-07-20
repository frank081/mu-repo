'''
Some things we may want to support in the future (and if not, at least keep for referencing):

Searching (http://gitster.livejournal.com/30195.html)
    git grep -l --all-match -e Bar -e Foo
    git log --all-match --grep=APSTUD
    
http://stackoverflow.com/questions/61002/how-can-i-generate-a-git-diff-of-whats-changed-since-the-last-time-i-pulled
git pull origin
git diff @{1}..

Interesting:
    http://www.saintsjd.com/2012/01/a-better-ui-for-git/ -- https://github.com/saintsjd/gum
    
Commands TODO:

git stage = git add -A
git stage -i= interactively stage files


git unstage = git reset HEAD
git unstage -i= interactively unstage files

git ignore

Comparing 2 branches:
git log --left-right --graph --cherry-pick --oneline etk10-9.9.9...master
'''

#--------------------------------------------------------------------------------------------- SCITE
'''
Using SciTE:

Grab it from: http://www.scintilla.org/SciTEDownload.html
Put contents in SciTE.properties or %USERPROFILE%\SciTEUser.properties

Configuration:
#Edited from instructions on: http://www.scintilla.org/SciTEDoc.html

#Monospaced
font.base=$(font.monospace)
font.small=$(font.monospace)
font.comment=$(font.monospace)
font.text=$(font.monospace)
font.text.comment=$(font.monospace)
font.embedded.base=$(font.monospace)
font.embedded.comment=$(font.monospace)
font.vbs=$(font.monospace)
position.maximize=true

#Line numbers
line.margin.visible=1
line.margin.width=3+

#Better antialiasing on Vista onwards.
technology=1

#With git, always work with LF!
eol.mode=LF

#These are here but they only work in %USERPROFILE%\SciTEUser.properties!
position.left=300
position.top=100
position.width=800
position.height=600
position.maximize=0
'''