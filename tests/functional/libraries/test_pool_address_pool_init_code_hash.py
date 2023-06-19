def test_pool_address_pool_init_code_hash(pool_address_lib):
    assert pool_address_lib.poolInitCodeHash() == pool_address_lib.POOL_INIT_CODE_HASH()
