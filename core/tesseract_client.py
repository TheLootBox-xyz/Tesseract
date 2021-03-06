import json
import os

import dearpygui.dearpygui as dpg
import eth_utils
from cryptography.fernet import Fernet

from env_vars import (
    gas_price,
    lootbox_contract_rinkeby,
    web3_local_rinkeby,
    web3_arbitrum_rinkeby,
    dai_contract_rinkeby,
    dev
)

dpg.create_context()

web3_arbitrum_rinkeby.eth.account.enable_unaudited_hdwallet_features()

accounts_list = []

with dpg.font_registry():
    default_font = dpg.add_font("../fonts/m5x7.ttf", 25)
    created_account_font = dpg.add_font("../fonts/m5x7.ttf", 18)


# ---------
# Callbacks
# ---------


def create_account(new_eth_account, mnemonic, wallet_key):
    if not os.path.exists("accounts.json"):
        no_plaintext = Fernet(wallet_key)
        mnemonic_phrase = no_plaintext.encrypt(bytes(mnemonic, encoding='utf8'))
        pub_address = no_plaintext.encrypt(bytes(new_eth_account.address, encoding='utf8'))
        private_key = no_plaintext.encrypt(bytes(new_eth_account.key.hex(), encoding='utf8'))

        decrypt_pub_address = no_plaintext.decrypt(pub_address).decode("utf-8")
        decrypt_mnemonic_phrase = no_plaintext.decrypt(mnemonic_phrase).decode("utf-8")
        decrypt_private_key = no_plaintext.decrypt(private_key).decode("utf-8")

        save_account_info(decrypt_pub_address, mnemonic_phrase, private_key)
        show_created_account_info("Account info", decrypt_pub_address, decrypt_private_key, wallet_key,
                                  decrypt_mnemonic_phrase)
    else:
        print("Account already exists!!!")


def save_account_info(decrypt_pub_address, mnemonic_phrase, private_key):
    account = {'number': int(0), 'public_address': decrypt_pub_address, 'private_key': str(private_key.decode("utf-8")),
               'mnemonic_phrase': str(mnemonic_phrase.decode("utf-8"))}
    accounts_list.append(account)

    json.dump(accounts_list, open('accounts.json', 'w'))


def create_eth_account_callback():
    new_eth_account, mnemonic = web3_arbitrum_rinkeby.eth.account.create_with_mnemonic()
    wallet_key = Fernet.generate_key().decode("utf-8")
    create_account(new_eth_account, mnemonic, wallet_key)


def import_address_callback(mnemonic_phrase):
    try:
        new_eth_account = web3_arbitrum_rinkeby.eth.account.from_mnemonic(str(mnemonic_phrase))
        wallet_key = Fernet.generate_key().decode("utf-8")
        create_account(new_eth_account, mnemonic_phrase, wallet_key)
    except eth_utils.exceptions.ValidationError as e:
        show_exception("Exception", e)


def import_multiple_accounts_callback(mnemonic_phrase, number_of_accounts):
    try:
        multiple_accounts_list = []
        wallet_key = Fernet.generate_key().decode("utf-8")
        no_plaintext = Fernet(wallet_key)

        if os.path.exists("accounts.json"):
            with open('accounts.json', 'r') as account_check:
                current_accounts = json.load(account_check)

        for account in range(int(number_of_accounts)):
            try:
                if current_accounts[account]:
                    print("Account exists!!!!!")
            except IndexError:
                multiple_accounts_list.append(account)

        for number in multiple_accounts_list:
            new_eth_account = web3_arbitrum_rinkeby.eth.account.from_mnemonic(mnemonic_phrase,
                                                                              account_path=f"m/44'/60'/0'/0/{number}")

            pub_address = no_plaintext.encrypt(bytes(new_eth_account.address, encoding='utf8'))
            private_key = no_plaintext.encrypt(bytes(new_eth_account.key.hex(), encoding='utf8'))

            account = {'number': int(number), 'public_address': str(pub_address.decode("utf-8")),
                       'private_key': str(private_key.decode("utf-8"))}
            show_created_account_info("Account info", pub_address, wallet_key, private_key, "")
            accounts_list.append(account)
        json.dump(accounts_list, open('accounts.json', 'w'))
        multiple_accounts_list.clear()

    except eth_utils.exceptions.ValidationError as e:
        show_exception("Exception", e)


def create_bundle_callback(account_id, wallet_key):
    selected_account, key = get_account_private_key(account_id, wallet_key)
    try:
        # Approve transaction
        approve = dai_contract_rinkeby.functions.approve('0xE742e87184f840a559d26356362979AA6de56E3E',
                                                         10000000000000000000).buildTransaction(
            {'chainId': 4, 'gas': web3_local_rinkeby.toWei('0.02', 'gwei'),
             'nonce': web3_local_rinkeby.eth.get_transaction_count(dev, 'pending'), 'from': selected_account})

        sign_approve = web3_arbitrum_rinkeby.eth.account.sign_transaction(approve, key)
        web3_local_rinkeby.eth.send_raw_transaction(sign_approve.rawTransaction)

        # Create bundle
        create_bundle = lootbox_contract_rinkeby.functions.createBundle(10000000000000000000).buildTransaction(
            {'chainId': 4, 'gas': web3_local_rinkeby.toWei('0.02', 'gwei'),
             'nonce': web3_local_rinkeby.eth.get_transaction_count(dev, 'pending'), 'from': selected_account})

        sign_create_bundle = web3_arbitrum_rinkeby.eth.account.sign_transaction(create_bundle, key)
        web3_arbitrum_rinkeby.eth.send_raw_transaction(sign_create_bundle.rawTransaction)

    except Exception as e:
        show_exception("Exception", e)


def show_specific_account(account_id, wallet_key):
    selected_account, key = get_account_private_key(account_id, wallet_key)
    show_created_account_info("Account info", selected_account, key, wallet_key, "")


def get_account_private_key(account_id, wallet_key):
    no_plaintext = Fernet(wallet_key)
    with open('accounts.json', 'r') as accounts_from_file:
        account_data_json = json.load(accounts_from_file)
        selected_account = account_data_json[int(account_id)]['public_address']
        key = no_plaintext.decrypt(
            bytes(account_data_json[int(account_id)]['private_key'], encoding='utf8'))
    return selected_account, key.decode('utf-8')


def send_ether_callback(to_account, amount, account_id, wallet_key):
    try:
        selected_account, key = get_account_private_key(account_id, wallet_key)

        tx = {
            'nonce': web3_arbitrum_rinkeby.eth.get_transaction_count(selected_account, 'pending'),
            'to': to_account,
            'value': web3_arbitrum_rinkeby.toWei(amount, 'ether'),
            'gas': web3_arbitrum_rinkeby.toWei('0.02', 'gwei'),
            'gasPrice': gas_price,
            'from': selected_account
        }

        sign = web3_arbitrum_rinkeby.eth.account.sign_transaction(tx, key)
        web3_arbitrum_rinkeby.eth.send_raw_transaction(sign.rawTransaction)
    except Exception as e:
        show_exception("Exception", e)


# ----------------
# Selection events
# ----------------

def on_selection(sender, unused, user_data):
    if user_data[1]:
        if user_data[2] == "Create account":
            create_eth_account_callback()
        if user_data[2] == "Create bundle":
            account_id = dpg.get_value(user_data[3])
            wallet_key = dpg.get_value(user_data[4])
            create_bundle_callback(account_id, wallet_key)
        if user_data[2] == "Account info":
            key_to_bytes = bytes(dpg.get_value(user_data[3]), encoding='utf8')
            show_specific_account(key_to_bytes, user_data[4])
        if user_data[2] == "Send Ether":
            to_account = user_data[3]
            amount = user_data[4]
            sender_id = user_data[5]
            unlock = user_data[6]
            send_ether_callback(to_account, amount, sender_id, unlock)
        if user_data[2] == "Import Account":
            import_address_callback(dpg.get_value(user_data[3]))
        if user_data[2] == "Import Multiple Accounts":
            import_multiple_accounts_callback(dpg.get_value(user_data[3]), dpg.get_value(user_data[4]))
    else:
        dpg.delete_item(user_data[0])


# ----------------
# Prompts
# ----------------

def close_window(sender, unused, user_data):
    dpg.delete_item(user_data[0])


def show_exception(title, e):
    with dpg.mutex():
        with dpg.window(label=title, width=700, height=400) as exception_modal_id:
            alert_message_group = dpg.add_group(horizontal=True)
            button_group = dpg.add_group()
            dpg.add_text(e, parent=alert_message_group)
            dpg.add_button(label="Ok", width=75,
                           user_data=(exception_modal_id, True, "Exception", e),
                           callback=close_window, parent=button_group)


def show_import_multiple_accounts_notification(title):
    with dpg.mutex():
        with dpg.window(label=title, width=700, height=400, modal=True) as multiple_modal_id:
            mnemonic_group = dpg.add_group()
            alert_message_group = dpg.add_group(horizontal=True)
            dpg.add_text("Input mnemonic", parent=mnemonic_group)
            mnemonic_phrase = dpg.add_input_text(parent=mnemonic_group)
            dpg.add_text("Input number of accounts", parent=mnemonic_group)
            number_of_accounts = dpg.add_input_text(parent=mnemonic_group)
            dpg.add_text("", parent=mnemonic_group)

            dpg.add_button(label="Ok", width=75,
                           user_data=(
                               multiple_modal_id, True, "Import Multiple Accounts", mnemonic_phrase,
                               number_of_accounts),
                           callback=on_selection, parent=alert_message_group)
            dpg.add_button(label="Cancel", width=75, user_data=(multiple_modal_id, False, "Import Multiple Accounts"),
                           callback=on_selection, parent=alert_message_group)


def show_import_account_notification(title, message):
    with dpg.mutex():
        with dpg.window(label=title, width=700, height=400, modal=True) as import_modal_id:
            input_mnemonic_group = dpg.add_group(horizontal=True)
            alert_message_group = dpg.add_group()
            selection_buttons_group = dpg.add_group(horizontal=True)
            dpg.add_text("Input mnemonic", parent=input_mnemonic_group)
            mnemonic_phrase = dpg.add_input_text(parent=input_mnemonic_group)
            dpg.add_button(label="Ok", width=75, user_data=(import_modal_id, True, "Import Account", mnemonic_phrase),
                           callback=on_selection, parent=selection_buttons_group)
            dpg.add_button(label="Cancel", width=75, user_data=(import_modal_id, False, "Import Account"),
                           callback=on_selection, parent=selection_buttons_group)
            dpg.add_text(message, parent=alert_message_group)


def show_send_ether_notification(title, to, amount, sender_account, unlock):
    with dpg.mutex():

        if to:
            with dpg.window(label=title, width=700, height=400, modal=True, no_close=True) as send_modal_id:
                alert_message_group = dpg.add_group(horizontal=True)
                dpg.add_button(label="Ok", width=75,
                               user_data=(send_modal_id, True, "Send Ether", to, amount, sender_account, unlock),
                               callback=on_selection, parent=alert_message_group)
                dpg.add_button(label="Cancel", width=75, user_data=(send_modal_id, False), callback=on_selection,
                               parent=alert_message_group)
        else:
            return


def show_created_account_info(title, decrypt_pub_address, decrypt_private_key, wallet_unlock_key,
                              decrypt_mnemonic_phrase):
    with dpg.mutex():
        with dpg.window(label=title, width=700, height=420):
            account_created_group = dpg.add_group()
            account_unlock_key_warning = dpg.add_group()
            dpg.add_text("Public address", parent=account_created_group)
            dpg.add_input_text(default_value=decrypt_pub_address, width=500,
                               parent=account_created_group, no_spaces=True, readonly=True)
            dpg.add_text("Account private key", parent=account_created_group)
            dpg.add_input_text(default_value=decrypt_private_key, width=580,
                               parent=account_created_group, no_spaces=True, readonly=True)
            dpg.add_text("Account unlock key", parent=account_created_group)
            dpg.add_input_text(default_value=wallet_unlock_key, width=510,
                               parent=account_created_group, no_spaces=True, readonly=True)
            dpg.add_text("Account mnemonic", parent=account_created_group)
            dpg.add_input_text(default_value=decrypt_mnemonic_phrase, width=620,
                               parent=account_created_group)
            dpg.add_text("", parent=account_unlock_key_warning)
            dpg.add_text("WARNING: Make sure to save your account unlock key!", parent=account_unlock_key_warning)
            dpg.add_text("This key will not be saved by the Tesseract Client.", parent=account_unlock_key_warning)
            dpg.bind_font(created_account_font)


def show_thelootbox_bundle_notification(title, message):
    with dpg.mutex():
        with dpg.window(label=title, width=700, height=400, modal=True) as bundle_modal_id:
            alert_message_group = dpg.add_group()
            selection_group = dpg.add_group(horizontal=True)

            dpg.add_text("Input account id", parent=alert_message_group)
            account_id = dpg.add_input_text(parent=alert_message_group, no_spaces=True)
            dpg.add_text("Input wallet unlock key", parent=alert_message_group)
            wallet_key = dpg.add_input_text(parent=alert_message_group, no_spaces=True)
            dpg.add_text(message, parent=alert_message_group)

            dpg.add_button(label="Ok", width=75, user_data=(bundle_modal_id, True, "Create bundle",
                                                            dpg.get_value(account_id),
                                                            dpg.get_value(wallet_key)),
                           callback=on_selection, parent=selection_group)

            dpg.add_button(label="Cancel", width=75, user_data=(bundle_modal_id, False), callback=on_selection,
                           parent=selection_group)


def show_info(title, message, selection_callback, function_name):
    with dpg.mutex():
        viewport_width = dpg.get_viewport_client_width()
        viewport_height = dpg.get_viewport_client_height()

        with dpg.window(label=title, modal=True, no_close=True) as info_modal_id:
            if function_name == "Transfer nft":
                alert_message_group = dpg.add_group(horizontal=True)
                dpg.add_text(message)
                dpg.add_button(label="Ok", width=75, user_data=(info_modal_id, True, function_name),
                               callback=selection_callback, parent=alert_message_group)
                dpg.add_button(label="Cancel", width=75, user_data=(info_modal_id, False), callback=selection_callback,
                               parent=alert_message_group)
    dpg.split_frame()
    width = dpg.get_item_width(info_modal_id)
    height = dpg.get_item_height(info_modal_id)
    dpg.set_item_pos(info_modal_id, [viewport_width // 2 - width // 2, viewport_height // 2 - height // 2])


# --------
# Draw GUI
# --------

with dpg.window(pos=(0, 370), label="Create TheLootBox bundle", width=800, height=600, collapsed=True):
    your_address_group = dpg.add_group(horizontal=True)
    your_address_group_two = dpg.add_group(horizontal=True)
    dpg.add_text("Create loot bundle", parent=your_address_group)

    dpg.add_button(pos=(10, 120), label="Create bundle",
                   callback=lambda: show_thelootbox_bundle_notification("Authorization required",
                                                                        "Approve transaction?"))
    dpg.bind_font(default_font)

with dpg.window(pos=(0, 335), label="Send Ether", width=800, height=600, collapsed=True):
    to_address_group = dpg.add_group(horizontal=True)
    amount_to_send_group = dpg.add_group(horizontal=True)
    sender_id_group = dpg.add_group(horizontal=True)
    account_unlock_group = dpg.add_group(horizontal=True)
    dpg.add_text("To", parent=to_address_group)
    to_address = dpg.add_input_text(parent=to_address_group, no_spaces=True)
    dpg.add_text("Amount", parent=amount_to_send_group)
    amount_of_ether = dpg.add_input_text(parent=amount_to_send_group, no_spaces=True)
    dpg.add_text("Account Id", parent=sender_id_group)
    sender_account_id = dpg.add_input_text(parent=sender_id_group, no_spaces=True)
    dpg.add_text("Wallet unlock key", parent=account_unlock_group)
    unlock_account = dpg.add_input_text(parent=account_unlock_group, no_spaces=True)
    dpg.add_button(pos=(10, 200), label="Send Ether",
                   callback=lambda: show_send_ether_notification("Authorization required",
                                                                 dpg.get_value(to_address),
                                                                 dpg.get_value(amount_of_ether),
                                                                 dpg.get_value(sender_account_id),
                                                                 dpg.get_value(unlock_account)))
    dpg.bind_font(default_font)

with dpg.window(pos=(0, 300), label="Account", width=800, height=600, collapsed=True):
    if not os.path.exists("accounts.json"):
        public_address = ""
    else:
        with open('accounts.json', 'r') as accounts:
            account_data = json.load(accounts)
            public_address = account_data[0]['public_address']

    public_address_group = dpg.add_group()
    dpg.add_text("Public address", parent=public_address_group)
    dpg.add_input_text(default_value=public_address, parent=public_address_group)
    dpg.add_text("Input your account id and wallet unlock key here",
                 parent=public_address_group)
    dpg.add_text("Account Id", parent=public_address_group)
    account_id_input = dpg.add_input_text(parent=public_address_group)
    dpg.add_text("Wallet unlock key", parent=public_address_group)
    wallet_key_input = dpg.add_input_text(parent=public_address_group)
    dpg.add_button(pos=(10, 300), label="Show account info",
                   callback=lambda: show_specific_account(dpg.get_value(account_id_input),
                                                          dpg.get_value(wallet_key_input)))
    dpg.bind_font(default_font)

with dpg.window(label="Create or import account", width=800, height=300) as modal_id:
    with dpg.mutex():
        dpg.add_text("Welcome to the Tesseract client!")
        create_account_group = dpg.add_group()
        dpg.add_button(pos=(10, 100), label="Create account", callback=create_eth_account_callback,
                       parent=create_account_group)
        dpg.add_button(pos=(10, 150), label="Import account",
                       callback=lambda: show_import_account_notification("Import account", "Approve?"),
                       parent=create_account_group)
        dpg.add_button(pos=(10, 200), label="Import multiple accounts",
                       callback=lambda: show_import_multiple_accounts_notification("Import multiple accounts"),
                       parent=create_account_group)

        dpg.bind_font(default_font)

with dpg.theme() as global_theme:
    with dpg.theme_component(dpg.mvAll):
        dpg.add_theme_color(dpg.mvThemeCol_TitleBgActive, (92, 184, 92), category=dpg.mvThemeCat_Core)
        dpg.add_theme_color(dpg.mvThemeCol_TitleBgCollapsed, (90, 120, 90), category=dpg.mvThemeCat_Core)
        dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 5, category=dpg.mvThemeCat_Core)

dpg.bind_theme(global_theme)
dpg.create_viewport(title='Tesseract client', width=800, height=700)
dpg.setup_dearpygui()
dpg.show_viewport()
dpg.start_dearpygui()
dpg.destroy_context()
