import pyfiglet
import inquirer
import typer
from tabulate import tabulate
from termcolor import colored
from TokenABI import TTKOj_ABi
from routerABI import UniswapV2sepolia
from internals import EOA, DataConverter, Uniswap,Web3_list, config


wallet1 = EOA(account=config.get('Account_Details', 'account'), private_key=config.get('Account_Details', 'private_key'))
wallet1.new_token(11155111, '0x75F94f04d2144cB6056CCd0CFF1771573d838974',TTKOj_ABi)
uniswap_v2_Sep = Uniswap(Web3_list[2],'0xC532a74256D3Db42D0Bf7a0400fEFDbad7694008',UniswapV2sepolia)
wallet1.new_route(uniswap_v2_Sep)


def main():
    main_panel = colored(pyfiglet.figlet_format("Web3", font='big'), color='light_blue')
    print(main_panel)
    option = inquirer.list_input("Choose your move ", choices=['Transfer', 'Chain list','Swap', 'Exit'])
    if option == 'Exit':
        On_going  = False
    else:
        On_going = True
    while On_going:  
        if option == 'Chain list':
            tabledata = DataConverter.chain_list_data(wallet1.chain_list())  
            headers = ["Chain ID", "⛓️Name"]
            print(tabulate(tabledata, headers, tablefmt="fancy_grid"))
            
        elif option == 'Transfer':
            filtered_token_list = [token.token_symbol() for token in wallet1.token_list if token.chain_id == wallet1.current_chain] + ['ETH']
            token = inquirer.list_input("Choose Token", choices=filtered_token_list)
            transfer_input = [
                inquirer.Text('chain', message='⛓️Input chain id', default=wallet1.current_chain),
                inquirer.Text('destination', message='Input destination address'),
                inquirer.Text('amount', message='Input amount'),
                inquirer.Text('gas', message='⛽Input gas', default='2000000')
            ]
            data_input = inquirer.prompt(transfer_input)
            txn_data = wallet1.transfer(int(data_input['chain']), data_input['destination'], data_input['amount'], token, int(data_input['gas']))
            print(f'🤑 {txn_data["amount"]} {txn_data["symbol"]}')
            print(f'from {txn_data["from"]} --> {txn_data["to"]}')
            print(f'nonce : {txn_data["nonce"]}  TXN_HASH : {txn_data["transaction hash"]}')

        elif option == 'Swap':
            filtered_route_list = [route for route in wallet1.router_list if route.chain_id == wallet1.current_chain ]
            router = inquirer.list_input("Choose router to swap", choices=filtered_route_list)
            filtered_token_list = [token.token_symbol() for token in wallet1.token_list if token.chain_id == wallet1.current_chain] + ['ETH']
            # Get the token to swap
            token_to_swap = None
            while token_to_swap is None:
                choice = inquirer.list_input("Choose TokenToSwap", choices=filtered_token_list+ ["Other"])
                if choice == "Other":
                    token_to_swap = inquirer.text("Enter the token address to swap")
                else:
                    token_to_swap = choice

            # Get the token to buy
            token_list = filtered_token_list.copy()
            token_list.remove(token_to_swap)
            token_to_buy = None
            while token_to_buy is None:
                choice = inquirer.list_input("Choose TokenToBuy", choices=token_list + ["Other"])
                if choice == "Other":
                    token_to_buy = inquirer.text("Enter the token address to buy")
                else:
                    token_to_buy = choice
            swap_input = [
                inquirer.Text('chain', message='⛓️Input chain id', default=wallet1.current_chain),
                inquirer.Text('amount', message='Input amount'),
                inquirer.Text('time out', message='Input time out'),
                inquirer.Text('gas', message='⛽Input gas', default='2000000')
            ]
            data_input = inquirer.prompt(swap_input)
            txn_data = wallet1.swap(int(data_input['chain']), token_to_swap, token_to_buy, data_input['amount'], router, data_input['time out'], int(data_input['gas']))
            print(f'nonce : {txn_data["nonce"]}  TXN_HASH : {txn_data["transaction hash"]}')
        elif option == 'Change network':
            chain_list = [str(jey)+ ':' + value for jey, value in wallet1.chain_list().items()]
            change_chain = inquirer.list_input("Choose network", choices=chain_list)
            wallet1.current_chain = change_chain.split(':')[0]
        else:
            print('Invalid option. Please try again.')
        opt = inquirer.list_input("What's your next move",choices=['Main','Change network', 'Exit'])
        option = opt
        if opt == 'Exit':
            On_going = False
        elif option == 'Main':
            option = inquirer.list_input("Choose your move ", choices=['Transfer', 'Chain list','Swap', 'Exit'])


if __name__ == "__main__":
    typer.run(main)
