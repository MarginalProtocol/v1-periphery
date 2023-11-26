import click

from ape import accounts, chain, project


def main():
    click.echo(f"Running deploy.py on chainid {chain.chain_id} ...")

    deployer_name = click.prompt("Deployer account name", default="")
    deployer = (
        accounts.load(deployer_name)
        if deployer_name != ""
        else accounts.test_accounts[0]
    )
    click.echo(f"Deployer address: {deployer.address}")
    click.echo(f"Deployer balance: {deployer.balance / 1e18} ETH")

    factory_address = click.prompt("Marginal v1 factory address", type=str)
    weth9_address = click.prompt("WETH9 address", type=str)
    publish = click.prompt("Publish to Etherscan?", default=False)

    # deploy marginal v1 position manager
    if click.confirm("Deploy Marginal v1 NFT position manager?"):
        click.echo("Deploying Marginal v1 NFT position manager ...")
        manager = project.NonfungiblePositionManager.deploy(
            factory_address,
            weth9_address,
            sender=deployer,
            publish=publish,
        )
        click.echo(f"Deployed Marginal v1 NFT position manager to {manager.address}")

    # deploy marginal v1 router
    if click.confirm("Deploy Marginal v1 router?"):
        click.echo("Deploying Marginal v1 router ...")
        router = project.Router.deploy(
            factory_address,
            weth9_address,
            sender=deployer,
            publish=publish,
        )
        click.echo(f"Deployed Marginal v1 router to {router.address}")

    # deploy marginal v1 quoter
    if click.confirm("Deploy Marginal v1 quoter?"):
        click.echo("Deploying Marginal v1 quoter ...")
        quoter = project.Quoter.deploy(
            factory_address,
            weth9_address,
            sender=deployer,
            publish=publish,
        )
        click.echo(f"Deployed Marginal v1 quoter to {quoter.address}")
