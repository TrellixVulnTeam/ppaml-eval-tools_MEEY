# submit.py -- submit info from run to galois     -*- coding: us-ascii -*-
# Copyright (C) 2014  Galois, Inc.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#   1. Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
#   2. Redistributions in binary form must reproduce the above copyright
#      notice, this list of conditions and the following disclaimer in
#      the documentation and/or other materials provided with the
#      distribution.
#   3. Neither Galois's name nor the names of other contributors may be
#      used to endorse or promote products derived from this software
#      without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY GALOIS AND OTHER CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED.  IN NO EVENT SHALL GALOIS OR OTHER
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
# PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
# LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""submit info from run to galois"""


# __init__.py ensured Python 2.6 or 2.7 is running.

from __future__ import (absolute_import, division, print_function)

from . import db
import os.path
from shutil import copyfile
from . import utility
import xdg.BaseDirectory



def run_tid_to_run(db, session, run_tid):
    """takes in possible run tag or id and returns corresponding run"""
    if run_tid.isdigit():
        run_id = int(run_tid)
    else:
        tag = session.query(db.Tag).filter_by(
          label = run_tid).scalar()
        run_id = tag.run_id if tag else None

    run = None if run_id == None else session.query(db.Run).filter_by(
      run_id = run_id).scalar()

    return run


def run_to_artifact_data(db, session, run):
    """takes in run and returns relevent artifact data"""
    artifact_id, output, trace = run.artifact_id, run.output, run.trace

    artifact = session.query(db.Artifact).filter_by(
      artifact_id = artifact_id).scalar()

    return artifact, artifact_id, output, trace


def copy_files_to_submit(srcdir, dstdir, filenames):
    for filename in filenames:
        srcpath = os.path.join(srcdir, filename)
        dstpath = os.path.join(dstdir, filename)
        copyfile(srcpath, dstpath)


def create_tables_to_submit(tmpdir, table_entries):
    try:
        index = db.Index(path=os.path.join(tmpdir, "submit.db"))
    except db.SchemaMismatch as exception:
        raise utility.FatalError(exception)
    else:
        with index.session() as session:
            for entry in table_entries:
                session.add(entry)

def package_directory(submitdir):
    pass

def submit_package(package):
    pass


#################################### Main #####################################
def main(arguments):
    """given a list of tags and run_ids this procedure packages up cooresponding
       artifact information, then submits it
    """
    try:
        index = db.Index.open_user_index()
    except db.SchemaMismatch as exception:
        raise utility.FatalError(exception)
    else:
        with index.session() as session:
            get_run = lambda run_tid: run_tid_to_run(index, session, run_tid)

            runs = [[],[]]
            for run_tid in arguments.run_tids:
                run = get_run(run_tid)
                runs[bool(run)].append(run if run else run_tid)

            if runs[False]:
                print("non-existant run_tids {0}".format(runs[False]),
                ": NO ACTION TAKEN")
                return # raise fatal exception instead of return

            runs = runs[True]

            # cannot move 'map' out of with statement, dependent on session
            get_artifact = lambda run: run_to_artifact_data(index, session, run)
            artifact_datas = map(get_artifact, runs)

    artifacts, filenames = [], []
    for artifact, artifact_id, output, trace in artifact_datas:
        if artifact_id not in filenames:
            artifacts.append(artifact)
            filenames.append(artifact_id)
            filenames.append(output)
            filenames.append(trace)

    srcdir = xdg.BaseDirectory.save_data_path('ppaml')
    with utility.TemporaryDirectory() as dstdir:
        create_tables_to_submit(dstdir, artifacts)
        copy_files_to_submit(srcdir, dstdir, filenames)

        package = package_directory(dstdir)
        submit_package(package)

    print("submit successful!")


def add_subparser(subparsers):
    """Register the 'add-team' subcommand."""
    parser = subparsers.add_parser(
      'submit',
      help="submit artifact data associated with tag or run_id")

    parser.add_argument('run_tids', type=str, nargs='+',
      help='list of tags or run_ids')

    parser.set_defaults(func=main)
