def test_pool_address_pool_init_code_hash(pool_address_lib, pool_init_code_hash_lib):
    assert (
        pool_init_code_hash_lib.poolInitCodeHash()
        == pool_address_lib.POOL_INIT_CODE_HASH()
    )
