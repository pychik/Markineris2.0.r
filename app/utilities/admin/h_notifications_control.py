from flask import render_template


def h_tg_notification_main():
    """
    main function for controlling tg notifications
    :return:
    """
    return render_template('admin/notifications_control/users_tg_control.html')
