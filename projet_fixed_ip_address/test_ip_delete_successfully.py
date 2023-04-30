## Tests that the IP address is deleted successfully. 
def test_ip_deleted_successfully(self, mocker):
    """
    Tests that the IP address is deleted successfully.
    """
    # Arrange
    mock_netbox_interface = mocker.Mock()
    mock_netbox_interface.mgmt_only = False
    mock_request_json = {
        "data": {
            "assigned_object_id": 1,
            "address": "192.168.1.1/24",
            "family": {"value": 4}
        },
        "event": "deleted"
    }
    mocker.patch("app.netbox_api.dcim.interfaces.get", return_value=mock_netbox_interface)
    mocker.patch("app.delete_ip_address")

    # Act
    response = mng_ip()

    # Assert
    assert response.status_code == 204
    app.delete_ip_address.assert_called_once_with(mock_netbox_interface, "192.168.1.1/24", 4)