from algopy import (
    ARC4Contract,
    UInt64,
    Account,
    Asset,
    LocalState,
    Global,
    Txn,
    itxn,
    gtxn,
)
from algopy.arc4 import abimethod


class SmartContractAuctionBe(ARC4Contract):
    # Auction
    # Start Price
    # Bid - Bid Price > Start Price
    # Bid - Bid Price > Previous Bid
    # Bidder != Previous Bidder
    # Bidder != Auction Owner
    # Start Time - End Time
    # Auction End -> End Time -> 0
    # Amount -> Claimble

    def __init__(self) -> None:
        self.end_time = UInt64(0)
        self.asa_amount = UInt64(0)  # Tong token dang co. Bid price > asa_amount
        self.asa = Asset()  # Token
        self.previous_bidder = Account()
        self.previous_bid = UInt64(0)
        self.claimable_amount = LocalState(
            UInt64, key="claim", description="The claimble amount"
        )  # key - value

    # Opt Asset
    @abimethod()
    def opt_into_asset(
        self, asset: Asset
    ) -> None:  # Dua sp dau gia vao, khi nay ASA dang empty
        assert Txn.sender == Global.creator_address, "Only creator can access"
        assert self.asa == 0, "ASA already exists"

        self.asa = asset

        # Transfer into this function
        itxn.AssetTransfer(
            xfer_asset=asset,
            asset_receiver=Global.current_application_address,
        ).submit()

        pass

    # Start Auction
    @abimethod()
    def start_auction(
        self,
        start_price: UInt64,
        duration: UInt64,
        axfer: gtxn.AssetTransferTransaction,
    ) -> None:  # Bdau dau gia
        assert (
            Txn.sender == Global.creator_address
        ), "Auction must be started by creator"
        assert self.end_time == 0, "Auction ended"
        assert (
            axfer.asset_receiver == Global.current_application_address
        ), "Axfer mustbe to this application"

        self.asa_amount = axfer.asset_amount
        # global -> unix time
        self.end_time = Global.latest_timestamp + duration
        self.previous_bidder = Txn.sender
        self.previous_bid = start_price

    @abimethod()
    def opt_in(self) -> None:
        pass

    # Bids
    @abimethod()
    def bid(self, payment_transaction: gtxn.PaymentTransaction) -> None:  # Dau gia
        assert Global.latest_timestamp < self.end_time, " Auction Ended"
        # Verify payment
        assert Txn.sender != self.previous_bidder, "Bidder can't bid twice in a row"
        assert Txn.sender == payment_transaction.sender, "Bidder is not available"
        assert (
            payment_transaction.amount > self.previous_bid
        ), "Bidder has to bid higher than previous bid"

        # Set bid info
        self.previous_bid = payment_transaction.amount
        self.previous_bidder = Txn.sender

        # Update claimble amount
        self.claimable_amount[Txn.sender] = payment_transaction.amount

    # Claim Bids
    @abimethod()
    def claim_asset(self, asset: Asset) -> None:  # Chuyen sp dau gia cho ng thang cuoc
        assert (
            Txn.sender == Global.creator_address
        ), "Auction must be started by creator"
        assert Global.latest_timestamp > self.end_time, "Auction has not ended yet"

        itxn.AssetTransfer(
            xfer_asset=asset,
            asset_receiver=self.previous_bidder,
            asset_close_to=self.previous_bidder,
            asset_amount=self.asa_amount,
        ).submit()

    @abimethod()
    def claim_bids(self) -> None:
        amount = original_amount = self.claimable_amount[Txn.sender]  # Lay dc token

        if Txn.sender == self.previous_bidder:
            amount -= self.previous_bid

        itxn.Payment(
            amount=amount,
            receiver=Txn.sender,
        ).submit()

        self.claimable_amount[Txn.sender] = original_amount - amount

    # Delete Application
    @abimethod(allow_actions=["DeleteApplication"])
    def delete_application(self) -> None:
        itxn.Payment(
            close_remainder_to=Global.creator_address,
            receiver=Global.creator_address,
        ).submit()

    def clear_state_program(self) -> bool:
        return True
