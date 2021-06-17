import pytest

from pdm.cli import actions
from pdm.models.specifiers import PySpecSet


@pytest.mark.usefixtures("repository")
def test_add_package(project, working_set, is_dev):
    actions.do_add(project, is_dev, packages=["requests"])
    section = (
        project.tool_settings["dev-dependencies"]["dev"]
        if is_dev
        else project.meta["dependencies"]
    )

    assert section[0] == "requests~=2.19"
    locked_candidates = project.locked_repository.all_candidates
    assert locked_candidates["idna"].version == "2.7"
    for package in ("requests", "idna", "chardet", "urllib3", "certifi"):
        assert package in working_set


@pytest.mark.usefixtures("repository")
def test_add_package_to_custom_section(project, working_set):
    actions.do_add(project, section="test", packages=["requests"])

    assert "requests" in project.meta.optional_dependencies["test"][0]
    locked_candidates = project.locked_repository.all_candidates
    assert locked_candidates["idna"].version == "2.7"
    for package in ("requests", "idna", "chardet", "urllib3", "certifi"):
        assert package in working_set


@pytest.mark.usefixtures("repository")
def test_add_package_to_custom_dev_section(project, working_set):
    actions.do_add(project, dev=True, section="test", packages=["requests"])

    dependencies = project.tool_settings["dev-dependencies"]["test"]
    assert "requests" in dependencies[0]
    locked_candidates = project.locked_repository.all_candidates
    assert locked_candidates["idna"].version == "2.7"
    for package in ("requests", "idna", "chardet", "urllib3", "certifi"):
        assert package in working_set


@pytest.mark.usefixtures("repository", "vcs")
def test_add_editable_package(project, working_set, is_dev):
    # Ensure that correct python version is used.
    project.environment.python_requires = PySpecSet(">=3.6")
    actions.do_add(project, is_dev, packages=["demo"])
    actions.do_add(
        project,
        is_dev,
        editables=["git+https://github.com/test-root/demo.git#egg=demo"],
    )
    section = (
        project.tool_settings["dev-dependencies"]["dev"]
        if is_dev
        else project.meta["dependencies"]
    )
    assert "demo" in section[0]
    assert "-e git+https://github.com/test-root/demo.git#egg=demo" in section[1]
    locked_candidates = project.locked_repository.all_candidates
    assert locked_candidates["demo"].revision == "1234567890abcdef"
    assert locked_candidates["idna"].version == "2.7"
    assert "idna" in working_set

    actions.do_sync(project, no_editable=True)
    assert not working_set["demo"].editable


@pytest.mark.usefixtures("repository", "working_set")
def test_add_remote_package_url(project, is_dev):
    actions.do_add(
        project,
        is_dev,
        packages=["http://fixtures.test/artifacts/demo-0.0.1-py2.py3-none-any.whl"],
    )
    section = (
        project.tool_settings["dev-dependencies"]["dev"]
        if is_dev
        else project.meta["dependencies"]
    )
    assert (
        section[0]
        == "demo @ http://fixtures.test/artifacts/demo-0.0.1-py2.py3-none-any.whl"
    )


@pytest.mark.usefixtures("repository")
def test_add_no_install(project, working_set):
    actions.do_add(project, sync=False, packages=["requests"])
    for package in ("requests", "idna", "chardet", "urllib3", "certifi"):
        assert package not in working_set


@pytest.mark.usefixtures("repository")
def test_add_package_save_exact(project):
    actions.do_add(project, sync=False, save="exact", packages=["requests"])
    assert project.meta.dependencies[0] == "requests==2.19.1"


@pytest.mark.usefixtures("repository")
def test_add_package_save_wildcard(project):
    actions.do_add(project, sync=False, save="wildcard", packages=["requests"])
    assert project.meta.dependencies[0] == "requests"


def test_add_package_update_reuse(project, repository):
    actions.do_add(project, sync=False, save="wildcard", packages=["requests", "pytz"])

    locked_candidates = project.locked_repository.all_candidates
    assert locked_candidates["requests"].version == "2.19.1"
    assert locked_candidates["chardet"].version == "3.0.4"
    assert locked_candidates["pytz"].version == "2019.3"

    repository.add_candidate("pytz", "2019.6")
    repository.add_candidate("chardet", "3.0.5")
    repository.add_candidate("requests", "2.20.0")
    repository.add_dependencies(
        "requests",
        "2.20.0",
        [
            "certifi>=2017.4.17",
            "chardet<3.1.0,>=3.0.2",
            "idna<2.8,>=2.5",
            "urllib3<1.24,>=1.21.1",
        ],
    )
    actions.do_add(
        project, sync=False, save="wildcard", packages=["requests"], strategy="reuse"
    )
    locked_candidates = project.locked_repository.all_candidates
    assert locked_candidates["requests"].version == "2.20.0"
    assert locked_candidates["chardet"].version == "3.0.4"
    assert locked_candidates["pytz"].version == "2019.3"


def test_add_package_update_eager(project, repository):
    actions.do_add(project, sync=False, save="wildcard", packages=["requests", "pytz"])

    locked_candidates = project.locked_repository.all_candidates
    assert locked_candidates["requests"].version == "2.19.1"
    assert locked_candidates["chardet"].version == "3.0.4"
    assert locked_candidates["pytz"].version == "2019.3"

    repository.add_candidate("pytz", "2019.6")
    repository.add_candidate("chardet", "3.0.5")
    repository.add_candidate("requests", "2.20.0")
    repository.add_dependencies(
        "requests",
        "2.20.0",
        [
            "certifi>=2017.4.17",
            "chardet<3.1.0,>=3.0.2",
            "idna<2.8,>=2.5",
            "urllib3<1.24,>=1.21.1",
        ],
    )
    actions.do_add(
        project, sync=False, save="wildcard", packages=["requests"], strategy="eager"
    )
    locked_candidates = project.locked_repository.all_candidates
    assert locked_candidates["requests"].version == "2.20.0"
    assert locked_candidates["chardet"].version == "3.0.5"
    assert locked_candidates["pytz"].version == "2019.3"


@pytest.mark.usefixtures("repository")
def test_add_package_with_mismatch_marker(project, working_set, mocker):
    mocker.patch(
        "pdm.models.environment.get_pep508_environment",
        return_value={"platform_system": "Darwin"},
    )
    actions.do_add(project, packages=["requests", "pytz; platform_system!='Darwin'"])
    assert "pytz" not in working_set


@pytest.mark.usefixtures("repository")
def test_add_dependency_from_multiple_parents(project, working_set, mocker):
    mocker.patch(
        "pdm.models.environment.get_pep508_environment",
        return_value={"platform_system": "Darwin"},
    )
    actions.do_add(project, packages=["requests", "chardet; platform_system!='Darwin'"])
    assert "chardet" in working_set


@pytest.mark.usefixtures("repository")
def test_add_packages_without_self(project, working_set):
    project.environment.python_requires = PySpecSet(">=3.6")
    actions.do_add(project, packages=["requests"], no_self=True)
    assert project.meta.name not in working_set


@pytest.mark.usefixtures("repository", "working_set")
def test_add_package_unconstrained_rewrite_specifier(project):
    project.environment.python_requires = PySpecSet(">=3.6")
    actions.do_add(project, packages=["django"], no_self=True)
    locked_candidates = project.locked_repository.all_candidates
    assert locked_candidates["django"].version == "2.2.9"
    project.meta.dependencies[0] == "django~=2.2"

    actions.do_add(
        project, packages=["django-toolbar"], no_self=True, unconstrained=True
    )
    locked_candidates = project.locked_repository.all_candidates
    assert locked_candidates["django"].version == "1.11.8"
    project.meta.dependencies[0] == "django~=1.11"
