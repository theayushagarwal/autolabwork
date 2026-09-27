cmake_minimum_required(VERSION 3.10)
project(solve)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(CURL REQUIRED)
find_package(nlohmann_json 3.2.0 REQUIRED)

# Primary executable: solve
add_executable(solve main.cpp)
target_link_libraries(solve PRIVATE CURL::libcurl nlohmann_json::nlohmann_json)

# Alias target so both 'solve' and 'autocode' work
add_executable(autocode main.cpp)
target_link_libraries(autocode PRIVATE CURL::libcurl nlohmann_json::nlohmann_json)
