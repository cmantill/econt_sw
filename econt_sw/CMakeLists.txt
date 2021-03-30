cmake_minimum_required(VERSION 2.6 FATAL_ERROR)
project( econt_sw )

include(CheckCXXCompilerFlag)
check_cxx_compiler_flag(-std=c++14 HAVE_FLAG_STD_CXX14)
if(HAVE_FLAG_STD_CXX14)
  set( CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=c++14" )
  message("will use c++14")
else()
    check_cxx_compiler_flag(-std=c++11 HAVE_FLAG_STD_CXX11)
    if(HAVE_FLAG_STD_CXX11)
      set( CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=c++11" )
      message("will use c++11")
    else()
      message( FATAL_ERROR "C++ 11 or higher is required")
    endif()
endif()

set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS}  -lzmq -lyaml-cpp -Wall -fPIC")

option( BUILD_ANALYSIS "Build and compile analysis tools" ON )
option( MONGOOSE_WEB_TOOL "Build and compile mongoose tool" OFF )

list(APPEND CMAKE_PREFIX_PATH $ENV{ROOTSYS})
list( APPEND CMAKE_MODULE_PATH ${PROJECT_SOURCE_DIR}/cmake )

find_package( Boost COMPONENTS thread system filesystem timer REQUIRED )
find_package( CACTUS REQUIRED )

include_directories( SYSTEM ${CMAKE_CURRENT_SOURCE_DIR}/sources/main/include ${Boost_INCLUDE_DIRS} ${UHAL_LOG_INCLUDE_PREFIX} ${UHAL_GRAMMARS_INCLUDE_PREFIX} ${UHAL_UHAL_INCLUDE_PREFIX} )
link_directories( ${link_directories} ${EXTERN_BOOST_LIB_PREFIX} ${UHAL_LOG_LIB_PREFIX} ${UHAL_GRAMMARS_LIB_PREFIX} ${UHAL_UHAL_LIB_PREFIX} )

file( GLOB sources ${PROJECT_SOURCE_DIR}/sources/main/src/*.cc )
file( GLOB headers ${PROJECT_SOURCE_DIR}/sources/main/include/*.h )
file( GLOB executables ${PROJECT_SOURCE_DIR}/sources/main/executables/*.cxx )

add_library(objectlib OBJECT ${sources})
message( "-- Main executables to be installed")
foreach( exec ${executables} )
	  message( "\t${exec}" )
	   get_filename_component(ex ${exec} NAME_WE)
	    add_executable( ${ex} ${exec} $<TARGET_OBJECTS:objectlib> ${headers} )
	     target_link_libraries( ${ex} ${Boost_LIBRARIES} boost_program_options boost_regex boost_serialization boost_chrono cactus_uhal_log cactus_uhal_grammars cactus_uhal_uhal )
	      install( TARGETS ${ex} DESTINATION ${PROJECT_SOURCE_DIR}/bin
                ARCHIVE DESTINATION ${PROJECT_SOURCE_DIR}/lib
			  LIBRARY DESTINATION ${PROJECT_SOURCE_DIR}/lib )
endforeach()

add_library( ${PROJECT_NAME} SHARED ${sources} )
target_link_libraries( ${PROJECT_NAME} ${Boost_LIBRARIES} boost_program_options boost_regex boost_serialization boost_chrono cactus_uhal_log cactus_uhal_grammars cactus_uhal_uhal )
target_include_directories( ${PROJECT_NAME} PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include )
install( TARGETS ${PROJECT_NAME}
         ARCHIVE DESTINATION ${PROJECT_SOURCE_DIR}/lib
	  LIBRARY DESTINATION ${PROJECT_SOURCE_DIR}/lib )

if( BUILD_ANALYSIS )
    #find_package( ROOT REQUIRED ) 
    #if( ROOT_FOUND )
    # 	include_directories( ${ROOT_INCLUDE_DIRS} )
    # 	link_libraries( ${ROOT_LIBRARIES} )
    #    add_definitions( ${ROOT_DEFINITIONS} )
    #endif()
    include_directories( ${CMAKE_CURRENT_SOURCE_DIR}/sources/analysis/include )
    file( GLOB sources ${sources} ${PROJECT_SOURCE_DIR}/sources/analysis/src/*.cc )
    file( GLOB headers ${headers} ${PROJECT_SOURCE_DIR}/sources/analysis/include/*.h )
    file( GLOB analysis_executables ${PROJECT_SOURCE_DIR}/sources/analysis/executables/*.cxx )
    message( "-- Analysis executables to be installed")
    add_library(anaobjectlib OBJECT ${sources})
    foreach( exec ${analysis_executables} )
    	          message( "\t${exec}" )
		       get_filename_component(ex ${exec} NAME_WE)
		            add_executable( ${ex} ${exec} $<TARGET_OBJECTS:anaobjectlib> ${headers} )
			         target_link_libraries( ${ex} ${Boost_LIBRARIES} boost_program_options boost_regex boost_serialization boost_chrono cactus_uhal_log cactus_uhal_grammars cactus_uhal_uhal )
				      install( TARGETS ${ex} DESTINATION ${PROJECT_SOURCE_DIR}/bin
             			            ARCHIVE DESTINATION ${PROJECT_SOURCE_DIR}/lib
					    	          LIBRARY DESTINATION ${PROJECT_SOURCE_DIR}/lib )
    endforeach()
endif( BUILD_ANALYSIS )
