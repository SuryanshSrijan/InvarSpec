#include <iostream>
#include <string>
#include <cassert>
#include <unistd.h>
#include <sys/wait.h>
#include <vector>
#include "cfg.hpp"

using namespace std;


void get_cfg(string exec_file, string cfg_file) {
	int chpid = fork();
	if(chpid == -1) {
		cerr << "Error in forking chind process" << endl;
		exit(1);
	}
	if(chpid == 0) {
		vector<string> arg_list = {"-qq", "-c", "aa; pdfj @ main > " + cfg_file, exec_file};
		vector<char *> args;
		for(string& arg: arg_list) args.push_back(&arg[0]);
		args.push_back(nullptr);
		execvp("r2", args.data()); 
	}
	else {
		int status;
		wait(&status);

		if(status != 0) {
			cerr << "Error in CFG creation" << endl;
			exit(1);
		}
	}
}

int main(int argc, char * argv[]) {
	assert(argc == 2);
	
	string exec_file = string(argv[1]);
	string cfg_file = exec_file + ".cfg";
	string ddg_file = exec_file + ".ddg";
	string ss_file  = exec_file + ".ss";

	get_cfg(exec_file, cfg_file);

	// CFG * cfg = new CFG(cfg_file);

}
