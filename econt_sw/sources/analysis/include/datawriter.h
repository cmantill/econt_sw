#ifndef DATAWRITER
#define DATAWRITER 1

#include <boost/function.hpp>
#include <boost/functional/factory.hpp>
#include <boost/bind.hpp>
#include <iostream>
#include <fstream>

#include "LinkAligner.h"

class Writer
{
 public:
 Writer(std::string aname) : m_name(aname) {;}
  virtual ~Writer() = default;
  virtual void fill(link_aligner_data data) {;}
  virtual void save(){;}

  void print(){
    std::cout << "saving data to " << m_name << std::endl;
  }
  friend std::ostream& operator<<(std::ostream& out,const Writer& w){
    out << w.m_name;
    return out;
  }
 protected: 
  std::string m_name;
};

class DelayScanCSVDataWriter : public Writer
{
 public:
  DelayScanCSVDataWriter(std::string aname);
  ~DelayScanCSVDataWriter();
  void fill(link_aligner_data data) ;
  void save();
 private:
  std::ofstream ofs;
};

/*
class RawDataWriter : public Writer
{ 
 public:
  RawDataWriter(std::string aname);
  ~RawDataWriter();
  void fill(raw_data data);
}
*/

class DataWriterFactory
{
 public:
  DataWriterFactory(){
    factoryMapStr["delayscan"] = boost::bind(boost::factory<DelayScanCSVDataWriter*>(), _1 );
  }
  ~DataWriterFactory(){;}
  
  std::unique_ptr<Writer> Create(const std::string& key, std::string aname ) const
    {
      std::unique_ptr<Writer> ptr{factoryMapStr.at(key)(aname)};
      return ptr;
    }
  
  std::unique_ptr<Writer> Create(const std::string& key, std::string aname, std::map<std::string,int> map ) const
    {
      std::unique_ptr<Writer> ptr{factoryMapStrMap.at(key)(aname,map)};
      return ptr;
    }
  
  std::unique_ptr<Writer> Create(const std::string& key, std::string aname, YAML::Node node ) const
    {
      std::unique_ptr<Writer> ptr{factoryNode.at(key)(aname,node)};
      return ptr;
    }
 private:
  std::map<std::string, boost::function<Writer* (const std::string&)>> factoryMapStr;
  std::map<std::string, boost::function<Writer* (const std::string&,const std::map<std::string,int>&)>> factoryMapStrMap;
  std::map<std::string, boost::function<Writer* (const std::string&,const YAML::Node&)>> factoryNode;
};

#endif
