import json
import re
from pathlib import Path
import json
#import plac
import urllib3
from datetime import datetime
urllib3.disable_warnings()
import requests
import urllib.parse
import logging
import requests 
#requests.packages.urllib3.add_stderr_logger()


#@plac.annotations(
#    input=("Input", "positional", None, str),
#    output_dir=("Output directory", "positional", None, str),
#    user=("User", "option", "u", str),
#    password=("Password", "option", "p", str),
#    sherpa=("Sherpa server url", "option", None, str),
#    project=("Sherpa project", "option", None, str),
#    annotator=("Sherpa annotator, default is first favorite.", "option", None, str)
#)
def sherpa_client(
        input,
        output_dir,
        user="stefan",
        password="MYPASSWORD",
        sherpa="https://cube.kairntech.com:9071",
        project="",
        annotator=""
):
    # Retrieve Bearer token from credentials
    token = get_token(sherpa, user, password)
    # here you can specify specific formatter (like the SCIA BEL formatter)
    #annotate_url = f"{sherpa}/api/annotate/projects/{project}/annotators/{annotator}/_annotate_format_binary"
    # here you will return json results
    #annotate_url = f"{sherpa}/api/annotate/projects/{project}/annotators/{annotator}/_annotate_binary"
    input_path = Path(input)
    if not input_path.exists():
        print("Input file not found", input_path, exit=1)
    if not Path(output_dir).exists():
        print("Output directory not found", output_dir, exit=1)
    if input_path.is_dir():
        for f in input_path.rglob("*.pdf"):
            print("processing %s ..." % f)
            annotate_file(f, output_dir, output_format='json', server=sherpa,
                          project=project, annotator=annotator, auth=token)
    else:
        print("processing %s ..." % input_path)
        annotate_file(input_path, output_dir, output_format='json',
                      server=sherpa, project=project,
                      annotator=annotator, auth=token)

# ask_question(q, RAGPROJECT, RAGPIPELINE, MYTOKENSANDBOX, SERVERSANDBOX)
def ask_question(question, project, pipeline, mytoken, server):
    #print("in ask_question: %s, %s, %s, %s, %s" % (question, project, pipeline, mytoken, server))
    headers = {
        'accept': 'application/json',
        'Authorization': 'Bearer ' + mytoken,
        'X-Requested-With': 'XMLHttpRequest',
    }
    
    safe_question = urllib.parse.quote_plus(question)
    #print("safe_question = %s" % safe_question)
    
    params = {
        'query': safe_question,
        'from': '0',
        'size': '10',
        'highlight': 'false',
        'facet': 'false',
        'simpleQuery': 'false',
        'invertSearch': 'false',
        'searchType': 'hybrid',
        'answerQuestion': 'true',
        'answerer': pipeline,
        'returnHits': 'true',
        'htmlVersion': 'false',
        'asyncAnswer': 'false',
    }
    #print("params = %s" % params)
    response = requests.post(
        f'{server}/api/projects/{project}/segments/_search',
        params=params,
        headers=headers,
    )

    if response.ok:
        #print("answer to question '%s': %s" % (question, response.text))
        return json.loads(response.text)
    else:
        print("Error asking question '%s': %s" % (question, response.text))
        return {}

def get_projects(json_text):
    jsondata = json.loads(json_text)
    #print("jsondata = %s" % jsondata)
    projectlist = []
    for j in jsondata:
        projectlist.append(j['name'])
    return projectlist
def get_annotators(json_text):
    jsondata = json.loads(json_text)
    #print("jsondata = %s" % jsondata)
    projectlist = []
    for j in jsondata['learner']:
        projectlist.append(j['name'])
    for j in jsondata['plan']:
        projectlist.append(j['name'])
    return projectlist
def annotate_file(input_path, output_dir, **kwargs):
    auth = kwargs['auth']
    server = kwargs['server']
    project = kwargs['project']
    annotator = kwargs['annotator']
    output_format = kwargs['output_format']
    headers = {'Authorization': 'Bearer ' + auth}

    file_name = str(Path(input_path.parts[-1]).with_suffix(".%s" % output_format))
    # if file_name end with txt
    inputfile = str(input_path)
    print("processing %s ..." % inputfile)
    # get the current date + time as YYYY-MM-DD-HH-MM-SS
    now = datetime.now()
    if project is None or project == "":
        print("projects on server %s ..." % server)
        p = requests.get(f"{server}/api/projects/", headers=headers, verify=False, timeout=1000)
        if p.ok:
            projects = get_projects(p.text)
            print("Available projects on server %s are: %s" % (server, projects))
            exit()
        else:
            print("Error retrieving projects from server %s: %s" % (server, p.text))
            exit()
    if annotator is None or annotator == "":
        print("annotators on server %s in project %s ..." % (server, project))
        a = requests.get(f"{server}/api/projects/{project}/annotators_by_type", headers=headers, verify=False, timeout=1000)
        if a.ok:
            annotators = get_annotators(a.text)
            print("Available annotators on server %s are: %s" % (server, annotators))
            exit()
        else:
            print("Error retrieving annotators from server %s: %s" % (server, a.text))
            exit()
    fin = open(inputfile, "rb")
    if inputfile.endswith(".txt"):
        annotate_url = f"{server}/api/annotate/projects/{project}/annotators/{annotator}/_annotate"
        headers['Content-Type'] = 'text/plain'
        r = requests.post(annotate_url,
                          data=open(inputfile, "rb"),
                          headers=headers, verify=False, timeout=1000)
    else:
        print("processing binary file %s ..." % inputfile)
        annotate_url = f"{server}/api/annotate/projects/{project}/annotators/{annotator}/_annotate_binary"
        print("url = %s" % annotate_url)
        r = requests.post(annotate_url,
                          files={'file': (inputfile, fin)},
                          # files={'file': fin},
                          headers=headers, verify=False, timeout=1000)
    if r.ok:
        #print("returned from server: %s" % r.content)
        jsonresult = json.loads(r.content)
        return jsonresult[0]
        #output_file = Path(output_dir) / file_name
        #with output_file.open("wb") as fout:
        #    fout.write(r.content)
    else:
        print("Error processing file %s: %s, %s" % (input_path, r.text, r.status_code))
        # add this line at the end of the logfile
        return {}
        with open("logfile.log", "a") as f:
            f.write("%s: Error processing file %s: %s\n" % (now, input_path, r.text))

def annotate_text(text, output_dir, **kwargs):
    auth = kwargs['auth']
    server = kwargs['server']
    project = kwargs['project']
    annotator = kwargs['annotator']
    output_format = kwargs['output_format']
    headers = {'Authorization': 'Bearer ' + auth}
    print("annotate text '%s' with project '%s' and annotator '%s' on server '%s' ..." % (text, project, annotator, server))
    now = datetime.now()
    if project is None or project == "":
        print("projects on server %s ..." % server)
        p = requests.get(f"{server}/api/projects/", headers=headers, verify=False, timeout=1000)
        if p.ok:
            projects = get_projects(p.text)
            print("Available projects on server %s are: %s" % (server, projects))
            exit()
        else:
            print("Error retrieving projects from server %s: %s" % (server, p.text))
            exit()
    if annotator is None or annotator == "":
        print("annotators on server %s in project %s ..." % (server, project))
        a = requests.get(f"{server}/api/projects/{project}/annotators_by_type", headers=headers, verify=False, timeout=1000)
        if a.ok:
            annotators = get_annotators(a.text)
            print("Available annotators on server %s are: %s" % (server, annotators))
            exit()
        else:
            print("Error retrieving annotators from server %s: %s" % (server, a.text))
            exit()

    annotate_url = f"{server}/api/annotate/projects/{project}/annotators/{annotator}/_annotate"
    headers['Content-Type'] = 'text/plain'
    r = requests.post(annotate_url,
                      data=text,
                      headers=headers, verify=False, timeout=1000)

    if r.ok:
        print("returned from server: %s" % r.content)
        jsonresult = json.loads(r.content)
        if type(jsonresult) == list and len(jsonresult) > 0:
            return jsonresult[0]
        else:
            print("result in annotate_text is not a list: %s" % jsonresult)
            #return {}
            return jsonresult
        #output_file = Path(output_dir) / file_name
        #with output_file.open("wb") as fout:
        #    fout.write(r.content)
    else:
        # get the reason for the error
        print("Error '%s' when processing text: %s" % (r.reason, r.text))
        # add this line at the end of the logfile
        return {}
        with open("logfile.log", "a") as f:
            f.write("%s: Error processing text: %s\n" % (now, r.text))


# retrieve Authorization bearer token from user/password
def get_token(server, user, password):
    url = f"{server}/api/auth/login"
    auth = {"email": user, "password": password}
    try:
        response = requests.post(url, json=auth,
                                 headers={'Content-Type': "application/json", 'Accept': "application/json"},
                                 verify=False)
        json_response = json.loads(response.text)
    except Exception as ex:
        print("Error connecting to Sherpa server %s: %s" % (server, ex))
        return
    if 'access_token' in json_response:
        token = json_response['access_token']
        return token
    else:
        print("Error retrieving token from Sherpa server %s: %s" % (server, json_response))
        return


#if __name__ == '__main__':
#    plac.call(sherpa_client)

