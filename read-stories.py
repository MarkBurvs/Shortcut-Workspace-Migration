import json
import os
import sys
import requests
# =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
# CONFIGURATION
# Specify your access tokens for the source and target workspaces here:
source_api_token='xxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxx'
target_api_token='xxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxx'
# Specify the source Team name here (make sure ALL stories you want to migrate are assigned to this team)
source_team_name = "Developers"
# Specify the source Workflow. The target Workspace MUST contain an identically named Workflow with identical state names
name_of_workflow ="Standard"
# =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
api_url_base = 'https://api.app.shortcut.com/api/v3'
search_endpoint = '/search/stories'
stories_endpoint = '/stories'
source_standard_workflow_state_ids={}
target_standard_workflow_state_ids={}
source_member_ids=[]
target_member_ids=[]
errors=[]

def paginate_results(next_page_data):
    try:
        url = 'https://api.app.shortcut.com' + next_page_data + '&token='+source_api_token
        response = requests.get(url)
        response.raise_for_status()
        # print("========= NEW PAGE ============")
        # print("paginate response ",response.content)
    except requests.exceptions.RequestException as e:
        print(e)
        sys.exit(1)
    return response.json()

def get_request(endpoint, token, query):
    try:
        url = api_url_base + endpoint + '?token='+token
        response = requests.get(url, params=query)
        response.raise_for_status()
        # print("response ",response.content)
    except requests.exceptions.RequestException as e:
        print(e)
        sys.exit(1)
    return response.json()

def get_workflow_ids():
    # the source ids
    sourceWorkflows = get_request("/workflows",source_api_token, {})
    sourceStandardWorkflow = list(filter(lambda x:x["name"]==name_of_workflow,sourceWorkflows))[0]
    states = sourceStandardWorkflow["states"]
    for state in states:
        source_standard_workflow_state_ids[state["name"]]=state["id"]
    print(source_standard_workflow_state_ids)
    # the target workflow ids
    targetWorkflows = get_request("/workflows",target_api_token, {})
    targetStandardWorkflow = list(filter(lambda x:x["name"]==name_of_workflow,targetWorkflows))[0]
    states = targetStandardWorkflow["states"]
    for state in states:
        target_standard_workflow_state_ids[state["name"]]=state["id"]
    print(target_standard_workflow_state_ids)
    return

def get_member_ids():
    # the source ids
    source_members = get_request("/members",source_api_token, {})
    for member in source_members:
        print(member["profile"]["name"])
        # print(member["id"])
        new_member = {}
        new_member["name"]=member["profile"]["name"] 
        new_member["id"]=member["id"]
        new_member["profile_id"]=member["profile"]["id"] 
        source_member_ids.append(new_member)
    # print("Source members",source_member_ids)
    # the target ids
    target_members = get_request("/members",target_api_token, {})
    for member in target_members:
        # print(member["profile"]["name"])
        # print(member["id"])
        new_member = {}
        new_member["name"]=member["profile"]["name"] 
        new_member["id"]=member["id"]
        new_member["profile_id"]=member["profile"]["id"] 
        target_member_ids.append(new_member)
    # print("Target members",target_member_ids)


def process_stories_for_new_workspace(all_stories):
    for source_story in all_stories:
        print("SOURCE STORY", source_story["name"])
        if source_story["archived"]:
            print("Is archived so skipping")
            continue
        fieldsToImport = [
            "name",
            "description",
            "created_at",
            "deadline",
            "estimate",
            "external_links",
            "story_type",
            "updated_at"
        ]
        new_story = {}
        # Remap the workflow states
        new_story["workflow_state_id"] = get_remapped_workflow_state(source_story["workflow_state_id"])

        # remap the owner IDs
        source_owner_ids=source_story["owner_ids"]
        target_owner_ids=[]
        # print("source_owner_ids ",source_owner_ids)
        for owner_id in source_owner_ids:
            # print("owner_id ",owner_id)
            get_remapped_member(owner_id)
            target_owner_ids.append(get_remapped_member(owner_id))
        new_story["owner_ids"] = target_owner_ids

        # Remap the requester ID
        new_story["requested_by_id"] = get_remapped_member(source_story["requested_by_id"])

        # Remap tasks
        source_tasks=source_story["tasks"]
        target_tasks=[]
        for source_task in source_tasks:
            # print("source_task ",source_task)
            new_task = {}
            new_task["complete"] = source_task["complete"]
            new_task["created_at"] = source_task["created_at"]
            new_task["description"] = source_task["description"]
            new_task["updated_at"] = source_task["updated_at"]
            new_task_owners = []
            for owner_id in source_task["owner_ids"]:
                new_task_owners.append(get_remapped_member(owner_id))
            new_task["owner_ids"] = new_task_owners
            target_tasks.append(new_task)
        new_story["tasks"] = target_tasks

        # Remap comments
        source_comments=source_story["comments"]
        target_comments=[]
        for source_comment in source_comments:
            # print("source_comment ",source_comment["text"])
            if source_comment["deleted"]:
                continue
            new_comment = {}
            new_comment["author_id"] = get_remapped_member(source_comment["author_id"])
            # new_comment["blocker"] = source_comment["blocker"]
            # new_comment["unblocks_parent"] = source_comment["unblocks_parent"]
            new_comment["created_at"] = source_comment["created_at"]
            # new_comment["parent_id"] = source_comment["parent_id"]
            new_comment["text"] = source_comment["text"]
            new_comment["updated_at"] = source_comment["updated_at"]
            target_comments.append(new_comment)
        new_story["comments"] = target_comments
        # TODO should really fix parenting of comments. 
        # So at this step, after they've all been created, we should cycle back through the source ones, 
        # and see if any have parent comments, and if so, remap them to the new ids.

        # All other simple fields
        for fieldToImport in fieldsToImport:
            # print("fieldToImport", fieldToImport)
            new_story[fieldToImport] = source_story[fieldToImport]
        # print("NEW STORY", new_story["name"])
        write_story(new_story)
    

def get_remapped_workflow_state(source_workflow_state_id):
    target_workflow_state_id = 0
    for workflowState in source_standard_workflow_state_ids:
        # print("source workflowState", workflowState)
        # print("source workflowState id", source_standard_workflow_state_ids[workflowState])
        if source_standard_workflow_state_ids[workflowState]==source_workflow_state_id:
            target_workflow_state_id = target_standard_workflow_state_ids[workflowState]
    return target_workflow_state_id

def get_remapped_member(source_member_id):
    # print("Getting remapped member for ",source_member_id)
    target_member_id = 0
    for source_member in source_member_ids:
        # print("source member", source_member)
        # print("source member id", source_member["id"])
        if source_member["id"]==source_member_id:
            for target_member in target_member_ids:
                if target_member["profile_id"]==source_member["profile_id"]:
                    target_member_id = target_member["id"]
                    # print("Target Member" ,target_member)
                    # print("Target Member id" ,target_member_id)
                    return target_member_id

def write_story(story):
    url = api_url_base + stories_endpoint + '?token='+target_api_token
    test_story='{"name": "Test7 name", "description": "Test4 description", "workflow_state_id":500000362}'
    # print(url)
    print("WRITING STORY ",story)
    try:
        response = requests.post(url, json=story)
        # response = requests.post(url, json.loads(test_story))
        response.raise_for_status()
        print("response ",response.content)
    except requests.exceptions.RequestException as e:
        print(e)

        errors.append("Failed writing "+story["name"])
        # sys.exit(1)
    return response.json()


def fetchAllStories():
    all_stories = []
    search_results = get_request(search_endpoint, source_api_token, {'query': 'team:'+source_team_name, 'page_size': 5, "detail":"full"})
    print(search_results['data'])
    while search_results['next'] is not None:
        for story in search_results['data']:
            print("STORY ", story['name'])
            all_stories.append(story)
        search_results = paginate_results(search_results['next'])
    else:
        for story in search_results['data']:
            print("STORY ", story['name'])
            all_stories.append(story)

        print("=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=")
        print('Stories all read')
    return all_stories
    

def main():
    get_member_ids()
    get_workflow_ids()
    all_stories = fetchAllStories()
    process_stories_for_new_workspace(all_stories)
    print("FINISHED. ",len(all_stories), "stories migrated.")
    if len(errors)==0:
        print("No errors")
    else:
        for error in errors:
            print(error)
    


if __name__ == "__main__":
    main()
    # write_story()
