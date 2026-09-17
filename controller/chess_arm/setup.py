from setuptools import find_packages, setup

package_name = 'chess_arm'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    package_data={
        'chess_arm': ['sq_dict.json'],
    },
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('lib/chess_arm', ['chess_arm/sq_dict.json']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='anup',
    maintainer_email='aashkashah1234@gmail.com',
    description='TODO: Package description',
    license='TODO: License declaration',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'arm_action_server = chess_arm.arm_action_server:main',
            'arm_action_client = chess_arm.arm_action_client:main',
            'ik_node = chess_arm.ik_node:main',
            'test_square = chess_arm.test_square:main',
        ],
    },
)
