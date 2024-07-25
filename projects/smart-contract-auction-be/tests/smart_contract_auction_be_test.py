from collections.abc import Generator

import pytest
import time
from algopy_testing import AlgopyTestContext, algopy_testing_context

from smart_contracts.smart_contract_auction_be.contract import SmartContractAuctionBe


@pytest.fixture()
def context() -> Generator[AlgopyTestContext, None, None]:
    with algopy_testing_context() as ctx:
        yield ctx
        ctx.reset()


def test_opt_into_asset(context: AlgopyTestContext) -> None:
    # Create an asset - fuzzing test
    asset = context.any_asset()  # asset - token
    contract = SmartContractAuctionBe()  # init contract

    contract.opt_into_asset(asset)

    assert contract.asa.id == asset.id, "Wrong ASA"

    inner_txn = context.last_submitted_itxn.asset_transfer
    assert (
        inner_txn.asset_receiver == context.default_application.address
    ), "Wrong address"

    assert inner_txn.xfer_asset == asset


def test_start_auction(context: AlgopyTestContext) -> None:
    # current + duration -> end
    current_timestamp = context.any_uint64(1, 1000)
    duration_timestamp = context.any_uint64(100, 1000)
    start_price = context.any_uint64()
    axfer_txn = context.any_asset_transfer_transaction(
        asset_amount=start_price,
        asset_receiver=context.default_application.address,
    )

    contract = SmartContractAuctionBe()
    contract.asa_amount = start_price

    context.patch_global_fields(latest_timestamp=current_timestamp)
    context.patch_txn_fields(sender=context.default_creator)

    contract.start_auction(
        start_price=start_price, duration=duration_timestamp, axfer=axfer_txn
    )

    assert (
        contract.end_time == current_timestamp + duration_timestamp
    ), "Timestamp not match"
    assert contract.previous_bid == start_price, "Gia bid trc do phai bang gia khoi tao"
    assert contract.asa_amount == start_price, "Gia khoi tao ko dong nhat"


def test_bid(context: AlgopyTestContext) -> None:
    # account
    account = context.default_creator  # Ng goi contract
    # auction_end
    auction_end = context.any_uint64(min_value=int(time.time() + 10000))
    # previous_bid
    previous_bid = context.any_uint64(1, 100)
    # amount
    payment_amount = context.any_uint64()

    contract = SmartContractAuctionBe()
    contract.end_time = auction_end
    contract.previous_bid = previous_bid
    payment = context.any_payment_transaction(sender=account, amount=payment_amount)

    contract.bid(payment)

    # assert
    assert contract.previous_bid == payment_amount
    assert contract.previous_bidder == account
    assert contract.claimable_amount[account] == payment_amount


def test_claim_bids(context: AlgopyTestContext) -> None:
    account = context.any_account()

    context.patch_txn_fields(sender=account)

    contract = SmartContractAuctionBe()

    claimable_amount = context.any_uint64()  # luong token tong

    # -> address -> amount
    contract.claimable_amount[account] = claimable_amount
    contract.previous_bidder = account
    previous_bid = context.any_uint64(max_value=int(claimable_amount))
    contract.previous_bid = previous_bid

    # series cac func hoac rieng tung func
    contract.claim_bids()

    amount = claimable_amount - previous_bid  # luong token du
    last_txn = context.last_submitted_itxn.payment

    assert last_txn.amount == amount, ""
    assert last_txn.receiver == account, ""
    assert contract.claimable_amount[account] == claimable_amount - amount
