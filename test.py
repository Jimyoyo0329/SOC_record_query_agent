def convert_little_to_big(hex_data, byte_size=4):
    """
    將小端順序的十六進制數據轉換為大端格式。
    
    :param hex_data: 十六進制字符串
    :param byte_size: 要處理的字節大小（4字節或8字節）
    :return: 大端格式的十六進制字符串
    """
    # 每 `byte_size` 字節為一組，處理十六進制數據
    groups = [hex_data[i:i+byte_size*2] for i in range(0, len(hex_data), byte_size*2)]
    
    # 反轉字節順序（小端 -> 大端）
    big_endian_groups = []
    for group in groups:
        # 把每個字節組反轉
        big_endian_group = ''.join([group[i:i+2] for i in range(0, len(group), 2)][::-1])
        big_endian_groups.append(big_endian_group)
    
    # 將所有反轉後的字節組合成新的十六進制字符串
    big_endian_hex = ''.join(big_endian_groups)
    
    return big_endian_hex

# 提供的十六進制數據（由 %x 漏洞產生的數據）
hex_data = "9d83450804b00080489c3f7f68d80ffffffff19d81160f7f76110f7f68dc709d8218019d834309d834506f6369707b465443306c5f49345f74356d5f6c6c306d5f795f79336e6334326136613431ffba007df7fa3af8f7f76440242be00010f7e05ce9f7f770c0f7f685c0f7f68000ffbaa608f7df668df7f685c08048ecaffbaa6140f7f8af09804b000f7f68000f7f68e20ffbaa648f7f90d50f7f69890242be000f7f68000804b000ffbaa6488048c869d81160ffbaa634ffbaa6488048be9f7f683fc0ffbaa6fcffbaa6f4119d81160"

# 轉換每4字節從小端到大端
big_endian_4byte = convert_little_to_big(hex_data, byte_size=4)

# 轉換每8字節從小端到大端
big_endian_8byte = convert_little_to_big(hex_data, byte_size=8)

# 輸出結果
print("Big Endian (4 Byte): ", big_endian_4byte)
print("Big Endian (8 Byte): ", big_endian_8byte)
