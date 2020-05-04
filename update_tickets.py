import arrow
import attr
from bs4 import BeautifulSoup

from database import get_session
from entities import (
    JiraTicket,
    JiraWorkLog,
    get_ticket_status,
    get_with_updated_work_log,
)
from managers import get_jira_ticket_from_key, persist_jira_ticket
from jira.network import get_issues, get_project


def get_from_jira(project_key: str):
    project = get_project(project_key)
    issues = get_issues(project)
    session = get_session()

    for issue in issues:
        jira_ticket = JiraTicket(
            key=issue.key,
            status=issue.status,
            description=issue.description,
            updated=issue.updated,
            ticket_log=[
                JiraWorkLog(status=get_ticket_status(cl.status_to), updated=cl.updated)
                for cl in issue.changelog
            ],
        )
        persist_jira_ticket(jira_ticket, session)
    session.commit()


def load_from_file(file_handle):
    return BeautifulSoup(file_handle, "lxml")


def persist_to_database(soup):
    session = get_session()

    for item in soup.find_all("item"):
        key = item.key.text
        status = item.status.text
        description = item.description.text
        updated = item.updated.text

        result = get_jira_ticket_from_key(key, session)

        work_log = JiraWorkLog(
            status=get_ticket_status(status),
            updated=arrow.get(updated, "ddd, D MMM YYYY H:mm:ss Z").date(),
        )
        attr.validate(work_log)

        if result is None:
            jira_ticket = JiraTicket(
                key=key,
                status=work_log.status,
                description=description,
                updated=work_log.updated,
                ticket_log=[],
            )
            attr.validate(jira_ticket)
        else:
            jira_ticket = result

        updated_ticket = get_with_updated_work_log(jira_ticket, work_log)
        persist_jira_ticket(updated_ticket, session)

    session.commit()
    session.close()
