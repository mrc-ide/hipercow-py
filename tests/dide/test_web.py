import responses

from hipercow.dide import web


def create_client(*, logged_in=True):
    cl = web.DideWebClient(web.Credentials("", ""))
    if logged_in:
        cl._client._has_logged_in = True
    return cl


@responses.activate
def test_list_headnodes():
    ## https://stackoverflow.com/questions/40361308/create-a-functioning-response-object
    responses.add(
        responses.POST,
        "https://mrcdata.dide.ic.ac.uk/hpc/_listheadnodes.php",
        body="foo\nbar\n",
        status=200,
    )
    cl = create_client()
    res = cl.headnodes()
    assert res == ["foo", "bar"]
