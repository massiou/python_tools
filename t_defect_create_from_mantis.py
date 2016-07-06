#coding: utf-8

"""
   Add defects into MySQL database from Mantis project
"""

import mysql.connector
import argparse
import pytest

import boa.pardb.mantis as mantis
import config

# Globals
MANTIS_LOGIN = config.config['mantis_login']
MANTIS_PASSWORD = config.config['mantis_password']
DATABASE = config.config['database']
HOST = config.config['host']
USER = config.config['user']
PASSWORD = config.config['password']


def test_get_bugs():
    """
    Unitary test for get_bugs function
    """
    mantis_c = mantis.Mantis(MANTIS_LOGIN, MANTIS_PASSWORD)
    bugs = get_bugs(mantis_c, 'nightly_build', 'FC60X0_PARROT')

    assert isinstance(bugs, list)

@pytest.mark.parametrize("bug, script_expected",
                         [(193286, 'rob_send_command_at_boot'),
                          (191266, 'cmd_DLPE_(iPod_iAP2)')
                         ]
                        )
def test_get_bug_data(bug, script_expected):
    """
    Unitary test for get_bug_data function
    """

    mantis_c = mantis.Mantis(MANTIS_LOGIN, MANTIS_PASSWORD)
    bug_data, scripts_lst = get_bug_data(mantis_c, bug)

    assert script_expected in scripts_lst

    assert bug_data == mantis_c.get_bug_data(bug)



def add_defect(mysql_db, script_name, bug_id, project_name, plan_name, run_name, data=None):
    """
    :param mysql_db: database connection
    :param script_name
    :param bug_id: Mantis bug id
    :param project_name
    :param plan_name
    :param run_name
    :param data: bug data
    :return: None
    """

    if not data:
        data = {}

    cursor_c = mysql_db.cursor(buffered=True)

    query = """INSERT IGNORE INTO t_defect (script_name,
                                            defect_number,
                                            project_name,
                                            plan_name,
                                            run_name,
                                            summary,
                                            fixed_in_version,
                                            status, project,
                                            resolution)
               VALUES ('{0}','{1}','{2}','{3}','{4}', '{5}', '{6}', '{7}', '{8}', '{9}')""".format\
        (
            script_name,
            int(bug_id),
            project_name,
            plan_name,
            run_name,
            data.get('summary', ''),
            data.get('fixed_in_version', ''),
            data.get('status', ''),
            data.get('project', ''),
            data.get('resolution', ''))

    cursor_c.execute(query)
    mysql_db.commit()


def get_bugs(mantis_cnx, version, mantis_project):
    """
    :param mantis_cnx: mantis connection
    :param version: product version
    :param mantis_project
    :return: list of bugs id
    """
    project_id = mantis_cnx.get_project_id_from_name(mantis_project)
    bugs_lst = mantis_cnx.get_bugs_with_advanced_filter(p_project_id=project_id,
                                                        p_also_subprojects=True,
                                                        p_extra_filter={"version": "{}".format(version)})
    return bugs_lst


def get_bug_data(mantis_cnx, bug_id):
    """
    :param mantis_cnx: Mantis connection
    :param bug_id: Mantis bug id
    :return: script name, written in bug description
    """
    data_bug = mantis_cnx.get_bug_data(bug_id)
    analysis = data_bug.get("analysis_comments", "")

    if not analysis:
        return data_bug, []

    analysis = list(data_bug.get("analysis_comments", "").split(','))

    # clean script name filled in 'Analysis Comments' field in Mantis
    scripts_list = [script.replace('.py', '').strip().split('.')[-1] for script in analysis]

    return data_bug, scripts_list


def main():
    """
    Entry point
    :return: None
    """
    # Get arguments
    parser = argparse.ArgumentParser(description='Process arguments')
    parser.add_argument('-m', '--mantis_project', required=True, help='Mantis project name ex: "FC60X0_PARROT"')
    parser.add_argument('-p', '--project_name', required=True, help='testrail project ex: HipHop FC6000 4.50 OEM')
    parser.add_argument('-n', '--plan_name', required=True, help='plan name ex:"03.72.01"')
    parser.add_argument('-r', '--run_name', required=True, help='run name ex: "03.72.01 - P 256L_Generic_I2C"')
    args = parser.parse_args()

    mantis_project = args.mantis_project
    project_name = args.project_name
    plan_name = args.plan_name
    run_name = args.run_name

    # Connect to MySQL DB
    mysql_c = mysql.connector.connect(user=USER,
                                      password=PASSWORD,
                                      host=HOST,
                                      database=DATABASE)

    # Mantis connection
    mantis_c = mantis.Mantis(MANTIS_LOGIN, MANTIS_PASSWORD)

    # Get bugs list from project name
    bugs = get_bugs(mantis_c, plan_name, mantis_project)

    # Loop on bugs id list
    for bug in bugs:
        print bug
        data, scripts_lst = get_bug_data(mantis_c, bug)
        # Loop on scripts name related to current bug id
        for script in scripts_lst:
            print "Add defect in database: {} {} {} {} {}".format(script, bug, project_name, plan_name, run_name)
            add_defect(mysql_c, '{} - None'.format(script), bug, project_name, plan_name, run_name, data)


if __name__ == '__main__':
    main()


