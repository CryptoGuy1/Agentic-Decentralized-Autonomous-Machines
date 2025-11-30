require("@nomicfoundation/hardhat-toolbox");
require("dotenv").config();

/** @type import('hardhat/config').HardhatUserConfig */
module.exports = {
  solidity: {
    version: "0.8.20",
    settings: {
      optimizer: {
        enabled: true,
        runs: 200
      }
    }
  },
  networks: {
    hardhat: {
      chainId: 31337
    },
    fidesinnova: {
      url: "https://fidesf1-rpc.fidesinnova.io/",
      chainId: 706883,
      accounts: process.env.DEPLOYER_PRIVATE_KEY 
        ? [process.env.DEPLOYER_PRIVATE_KEY] 
        : [],
      gasPrice: "auto",
      timeout: 60000
    }
  },
  etherscan: {
    apiKey: {
      fidesinnova: "no-api-key-needed"
    },
    customChains: [
      {
        network: "fidesinnova",
        chainId: 706883,
        urls: {
          apiURL: "https://explorer.fidesinnova.io/api",
          browserURL: "https://explorer.fidesinnova.io"
        }
      }
    ]
  },
  paths: {
    sources: "./contracts",
    tests: "./test",
    cache: "./cache",
    artifacts: "./artifacts"
  }
};
