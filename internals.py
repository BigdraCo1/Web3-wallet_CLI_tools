from web3.middleware import geth_poa_middleware
from Rpc import rpc_endpoint
from yaspin import yaspin
from ethObj import ETH
from abc import ABC, abstractmethod
import time
from web3 import Web3
from configparser import ConfigParser

config = ConfigParser()
config.read('.example.config.ini')

Web3_list = [Web3(Web3.HTTPProvider(endpoint_uri=endpoint)) for endpoint in rpc_endpoint]


class Token:
    pass


class Router(ABC):
    def __init__(self, _chain: Web3, _router_address: str, _router_abi: list):
        self.__chain = _chain
        self.__address = _router_address
        self.__abi = _router_abi
        self.__contract = _chain.eth.contract(address=_router_address, abi=_router_abi)
        self.__name = ''

    @property
    @abstractmethod
    def contract(self):
        return self.__contract

    @property
    @abstractmethod
    def router_name(self):
        return self.__name

    @property
    @abstractmethod
    def chain_id(self):
        return self.__chain.eth.chain_id


class Uniswap(Router):
    def __init__(self, _chain: Web3, _router_address: str, _router_abi: list):
        super().__init__(_chain, _router_address, _router_abi)
        self.__chain = _chain
        self.__contract = _chain.eth.contract(address=_router_address, abi=_router_abi)
        self.__name = 'Uniswap'

    def swap(self, _TokenToSwap: str, _TokenToBuy: str, _address: str, _timeout: int):
        toSwap = Web3.to_checksum_address(_TokenToSwap)
        toBuy = Web3.to_checksum_address(_TokenToBuy)
        swap = self.contract.functions.swapExactETHForTokens(
            0, [toSwap, toBuy], _address, int(time.time()) + (60 * int(_timeout))
        )
        return swap

    @property
    def router_name(self):
        return self.__name

    @property
    def contract(self):
        return self.__contract

    @property
    def chain_id(self):
        return self.__chain.eth.chain_id


class DataConverter:

    @staticmethod
    def uri_to_name(_uri):
        parts = _uri.split('/')
        for part in parts:
            if '.' in part:
                _part = part.split('.')
                return _part[0]

    @staticmethod
    def chain_id_to_web3(_chain_id):
        for w3 in Web3_list:
            if w3.eth.chain_id == _chain_id:
                return w3

    @staticmethod
    def symbol_to_token_instance(_chain_id, _symbol: str, _token_list: list[Token]) -> Token | None:
        for token in _token_list:
            if token.token_symbol().lower() == _symbol.lower() and token.chain_id == _chain_id:
                return token
        return None

    @staticmethod
    def chain_list_data(_chain_list: dict) -> list:
        result = []
        for key, value in _chain_list.items():
            temp = [key, value]
            result.append(temp)
        return result


class Token:

    def __init__(self, _chain_id: int, _address: str, _abi: list) -> None:
        self.__token_address = _address
        self.__token_abi = _abi
        self.__chain_id = _chain_id
        self.__Web3 = DataConverter.chain_id_to_web3(_chain_id)
        self.__token_contract = self.__Web3.eth.contract(abi=_abi, address=_address)

    @property
    def token_address(self):
        return self.__token_address

    @property
    def chain_id(self):
        return self.__chain_id

    @property
    def token_contract(self):
        return self.__token_contract

    @property
    def token_chain(self):
        return self.__Web3

    def token_balance(self, _account, ):
        token_balance_raw = self.token_contract.functions.balanceOf(_account).call()
        return {'amount': self.token_contract.from_wei(token_balance_raw, 'ether'),
                'symbol': self.token_symbol()}

    def token_symbol(self) -> str:
        token_contract = self.token_contract
        return token_contract.functions.symbol().call()


class EOA:

    @yaspin(text='Building and Fetching RPC')
    def __init__(self, account, private_key):
        self.__account: str = account
        self.__private_key: str = private_key
        self.__Web3: list[Web3] = []
        for w3 in Web3_list:
            w3.middleware_onion.inject(geth_poa_middleware, layer=0)
            self.__Web3.append(w3)

        self.__Web3.sort(key=lambda w3: w3.eth.chain_id)
        self.__token_list: list[Token] = []
        self.__router_list: list[Router] = []
        self.__current_chain = 11155111

    @property
    def current_chain(self):
        return self.__current_chain

    @current_chain.setter
    def current_chain(self, _chain):
        self.__current_chain = _chain

    @yaspin(text='Fetching token')
    def token_name_list(self):
        return [token.token_symbol() for token in self.__token_list] + ['ETH']

    @property
    def token_list(self):
        return self.__token_list

    @yaspin(text='Fetching route')
    def router_name_list(self):
        return [router.router_name for router in self.__router_list]

    @property
    def router_list(self):
        return self.__router_list

    @yaspin(text='Adding new router')
    def new_route(self, _new_route: Router):
        self.__router_list.append(_new_route)
        return _new_route.router_name

    @yaspin(text='Adding new token')
    def new_token(self, _chain_id: int, _address: str, _abi: list):
        new_token = Token(_chain_id, _address, _abi)
        self.__token_list.append(new_token)
        return new_token.token_symbol()

    def search_chain(self, _chain) -> Web3 | None:
        if isinstance(_chain, int):
            left = 0
            right = len(self.__Web3) - 1
            while left <= right:
                mid = (left + right) // 2
                w3 = self.__Web3[mid]
                if w3.eth.chain_id == _chain:
                    return w3
                elif w3.eth.chain_id < _chain:
                    left = mid + 1
                else:
                    right = mid - 1

        return None

    @yaspin(text='Fetching data')
    def chain_list(self) -> dict:
        return {w3.eth.chain_id: DataConverter.uri_to_name(w3.provider.endpoint_uri) for w3 in self.__Web3}

    def transfer_eth(self, w3: Web3, _destination: str, _amount: float, _gas: int = 2000000):
        nonce = w3.eth.get_transaction_count(self.__account)
        transaction = {
            'nonce': nonce,
            'to': _destination,
            'value': w3.to_wei(_amount, "ether"),
            'gas': _gas,
            'gasPrice': w3.eth.gas_price
        }
        signed_txn = w3.eth.account.sign_transaction(transaction, self.__private_key)
        txn_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
        w3.eth.wait_for_transaction_receipt(txn_hash)
        w3.eth.get_transaction_receipt(txn_hash)
        info = w3.eth.get_transaction(transaction_hash=txn_hash)
        return {'amount': float(w3.from_wei(info['value'], 'ether')),
                'symbol': 'ETH',
                'from': info['from'],
                'to': info['to'],
                'nonce': info['nonce'],
                'transaction hash': w3.to_hex(txn_hash)}

    def transfer_erc20(self, w3: Web3, _destination: str, _amount: float, _token: Token, _gas: int = 2000000):
        nonce = w3.eth.get_transaction_count(self.__account)
        txn = _token.token_contract.functions.transfer(_destination,
                                                       w3.to_wei(_amount, 'ether')).build_transaction({
            'nonce': nonce,
            'gas': _gas,
            'gasPrice': w3.eth.gas_price
        })
        sign_txn = w3.eth.account.sign_transaction(txn, self.__private_key)
        transaction_hash = w3.eth.send_raw_transaction(sign_txn.rawTransaction)
        w3.eth.wait_for_transaction_receipt(transaction_hash=transaction_hash)
        receipt = w3.eth.get_transaction_receipt(transaction_hash=transaction_hash)
        info = w3.eth.get_transaction(transaction_hash=transaction_hash)
        transfer_event = _token.token_contract.events.Transfer().process_receipt(receipt)
        token_amount = transfer_event[0]['args']['value'] / 10 ** _token.token_contract.functions.decimals().call()
        return {'amount': token_amount,
                'symbol': _token.token_symbol(),
                'from': info['from'],
                'to': info['to'],
                'nonce': info['nonce'],
                'transaction hash': w3.to_hex(transaction_hash)}

    @yaspin(text='Transaction is pending')
    def transfer(self, _chain: str | int, _destination: str, _amount: float, _token: str, _gas: int = 2000000):
        w3 = self.search_chain(_chain)
        if _token.lower() == 'eth':
            return self.transfer_eth(w3, _destination, _amount, _gas)
        else:
            token = DataConverter.symbol_to_token_instance(_chain, _token, self.__token_list)
            return self.transfer_erc20(w3, _destination, _amount, token, _gas)

    @yaspin(text='Swapping')
    def swap(self, _chain: str | int, _tokenToSwap: str, _tokenToBuy: str, _amount: float, _router: Router,
             _timeout: int, _gas: int = 2000000):
        w3 = self.search_chain(_chain)
        if '0x' not in _tokenToSwap and _tokenToSwap.lower() != 'eth':
            tokenToSwap = DataConverter.symbol_to_token_instance(_chain, _tokenToSwap, self.__token_list)
            _tokenToSwap = tokenToSwap.token_address
        if '0x' not in _tokenToBuy and _tokenToBuy.lower() != 'eth':
            tokenToBuy = DataConverter.symbol_to_token_instance(_chain, _tokenToBuy, self.__token_list)
            _tokenToBuy = tokenToBuy.token_address
        token_to_swap = ETH[_chain] if _tokenToSwap.lower() == 'eth' else _tokenToSwap
        token_to_buy = ETH[_chain] if _tokenToBuy.lower() == 'eth' else _tokenToBuy
        swap = _router.swap(token_to_swap, token_to_buy, self.__account, _timeout)
        swap_txn = swap.build_transaction({
            'from': self.__account,
            'value': w3.to_wei(_amount, 'ether'),
            'gas': _gas,
            'gasPrice': w3.eth.gas_price,
            'nonce': w3.eth.get_transaction_count(account=self.__account)
        })
        signed_txn = w3.eth.account.sign_transaction(swap_txn, self.__private_key)
        tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
        w3.eth.wait_for_transaction_receipt(tx_hash)
        w3.eth.get_transaction_receipt(tx_hash)
        info = w3.eth.get_transaction(transaction_hash=tx_hash)
